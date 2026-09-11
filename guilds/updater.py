"""Local release-package updater with digest checks, path validation and rollback.

Manifests are trusted local release metadata. No arbitrary downloaded code is run.
A production remote update service should sign manifests with a pinned public key.
"""
from pathlib import Path,PurePosixPath
import hashlib,json,re,shutil,tempfile,zipfile,os

def version(value):
    if not re.fullmatch(r'\d+\.\d+\.\d+',value):raise ValueError('Use a three-part version')
    return tuple(map(int,value.split('.')))

def inspect_release(manifest_path,destination):
    manifest_path=Path(manifest_path).resolve();data=json.loads(manifest_path.read_text());version(data['version'])
    archive=(manifest_path.parent/data['archive']).resolve()
    if manifest_path.parent not in archive.parents:raise ValueError('Archive must be beside the trusted manifest')
    current=Path(destination)/'release.json';installed=json.loads(current.read_text())['version'] if current.exists() else '0.0.0'
    return {'available':version(data['version'])>version(installed),'installed':installed,'version':data['version'],'archive':str(archive),'sha256':data['sha256']}

def install_release(manifest_path,destination):
    release=inspect_release(manifest_path,destination)
    if not release['available']:return release
    archive=Path(release['archive'])
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=release['sha256']:raise ValueError('Release checksum mismatch')
    destination=Path(destination).resolve();destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.openiq-update-',dir=destination.parent) as tmp:
        stage=Path(tmp)/'stage';stage.mkdir()
        with zipfile.ZipFile(archive) as bundle:
            for entry in bundle.infolist():
                path=PurePosixPath(entry.filename)
                if path.is_absolute() or '..' in path.parts or '\\' in entry.filename or (entry.external_attr>>16)&0o170000==0o120000:
                    raise ValueError('Unsafe release entry')
                if entry.file_size>20*1024*1024:
                    raise ValueError('Oversized release entry')
            if sum(e.file_size for e in bundle.infolist())>100*1024*1024:
                raise ValueError('Release too large')
            bundle.extractall(stage)
        (stage/'release.json').write_text(json.dumps({'version':release['version']}))
        backup=Path(tmp)/'previous'
        if destination.exists():os.replace(destination,backup)
        try:os.replace(stage,destination)
        except OSError:
            if backup.exists():os.replace(backup,destination)
            raise
    return {**release,'installed':release['version'],'available':False}
