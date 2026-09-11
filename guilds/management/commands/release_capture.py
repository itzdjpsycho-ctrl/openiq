import hashlib,json,zipfile
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from guilds.updater import version
class Command(BaseCommand):
    help='Build a portable source release for the capture companion; does not publish it.'
    def add_arguments(self,p):p.add_argument('--version',default='0.1.0');p.add_argument('--output',required=True)
    def handle(self,*args,**o):
        version(o['version']);out=Path(o['output']);out.mkdir(parents=True,exist_ok=True);archive=out/('openiq-capture-'+o['version']+'.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for name in ['scripts/capture_desktop.py','guilds/capture.py','guilds/updater.py','guilds/__init__.py']:z.write(settings.BASE_DIR/name,name)
        manifest={'version':o['version'],'archive':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()};(out/'manifest.json').write_text(json.dumps(manifest,indent=2));self.stdout.write(str(out/'manifest.json'))
