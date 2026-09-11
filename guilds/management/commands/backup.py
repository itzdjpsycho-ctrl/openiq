"""Create private, consistent online SQLite snapshots with bounded retention."""
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Back up the SQLite database and active signing key without stopping the application.'

    def add_arguments(self, parser):
        parser.add_argument('--output', required=True, type=Path)
        parser.add_argument('--keep', type=int, default=7)
        parser.add_argument('--timeout', type=int, default=120)

    def handle(self, *args, **options):
        if options['keep'] < 1 or options['timeout'] < 1:
            raise CommandError('keep and timeout must be positive')
        database = settings.DATABASES['default']
        source = Path(database['NAME']).resolve()
        if database['ENGINE'] != 'django.db.backends.sqlite3' or not source.is_file():
            raise CommandError('Backup requires an existing file-backed SQLite database')
        output = options['output'].resolve()
        output.mkdir(parents=True, exist_ok=True, mode=0o700)
        deadline = time.monotonic() + options['timeout']

        def progress(status, remaining, total):
            if time.monotonic() > deadline:
                raise CommandError('Backup timed out; no completed snapshot was published')

        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        destination = output / ('openiq-backup-' + stamp)
        with tempfile.TemporaryDirectory(prefix='.openiq-backup-', dir=output) as temporary:
            stage = Path(temporary)
            snapshot = stage / 'db.sqlite3'
            with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as live:
                with closing(sqlite3.connect(snapshot)) as saved:
                    live.backup(saved, pages=256, progress=progress)
                    if saved.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                        raise CommandError('Snapshot failed SQLite integrity validation')
            # Capture the effective key, including deployments using SECRET_KEY.
            (stage / '.secret-key').write_text(settings.SECRET_KEY)
            files = {}
            for path in [snapshot, stage / '.secret-key']:
                path.chmod(0o600)
                with path.open('rb') as stream:
                    files[path.name] = hashlib.file_digest(stream, 'sha256').hexdigest()
            manifest = stage / 'manifest.json'
            manifest.write_text(json.dumps({'format': 'openiq-backup-v1', 'created': stamp, 'sha256': files}, indent=2) + '\n')
            manifest.chmod(0o600)
            os.rename(stage, destination)
        # Only prune this command's timestamped snapshot directories, never links.
        import re
        snapshots = sorted(path for path in output.iterdir() if re.fullmatch(r'openiq-backup-\d{8}T\d{12}Z', path.name) and path.is_dir() and not path.is_symlink())
        for old in snapshots[:-options['keep']]:
            shutil.rmtree(old)
        self.stdout.write(str(destination))
