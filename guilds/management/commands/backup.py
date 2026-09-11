"""Create private, consistent online SQLite snapshots with bounded retention."""
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from config.database import backend_for_database, DatabaseOperationError


class Command(BaseCommand):
    help = 'Back up the configured database and signing key using its maintenance adapter.'

    def add_arguments(self, parser):
        parser.add_argument('--output', required=True, type=Path)
        parser.add_argument('--keep', type=int, default=7)
        parser.add_argument('--timeout', type=int, default=120)

    def handle(self, *args, **options):
        if options['keep'] < 1 or options['timeout'] < 1:
            raise CommandError('keep and timeout must be positive')
        database = settings.DATABASES['default']
        backend = backend_for_database(database, settings.DATABASE_BACKEND)
        try:
            backend.validate_snapshot(database)
        except DatabaseOperationError as exc:
            raise CommandError(str(exc)) from exc
        output = options['output'].resolve()
        output.mkdir(parents=True, exist_ok=True, mode=0o700)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        destination = output / ('openiq-backup-' + stamp)
        with tempfile.TemporaryDirectory(prefix='.openiq-backup-', dir=output) as temporary:
            stage = Path(temporary)
            snapshot = stage / backend.snapshot_name
            try:
                backend.snapshot(database, snapshot, options['timeout'])
            except DatabaseOperationError as exc:
                raise CommandError(str(exc)) from exc
            # Capture the effective key, including deployments using SECRET_KEY.
            (stage / '.secret-key').write_text(settings.SECRET_KEY)
            files = {}
            for path in [snapshot, stage / '.secret-key']:
                path.chmod(0o600)
                with path.open('rb') as stream:
                    files[path.name] = hashlib.file_digest(stream, 'sha256').hexdigest()
            manifest = stage / 'manifest.json'
            manifest.write_text(json.dumps({'format': 'openiq-backup-v1', 'created': stamp, 'engine': database['ENGINE'], 'sha256': files}, indent=2) + '\n')
            manifest.chmod(0o600)
            os.rename(stage, destination)
        # Only prune this command's timestamped snapshot directories, never links.
        import re
        snapshots = sorted(path for path in output.iterdir() if re.fullmatch(r'openiq-backup-\d{8}T\d{12}Z', path.name) and path.is_dir() and not path.is_symlink())
        for old in snapshots[:-options['keep']]:
            shutil.rmtree(old)
        self.stdout.write(str(destination))
