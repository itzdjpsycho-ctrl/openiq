"""Boundary validation and failure recovery contracts."""
import json,tempfile,zipfile,hashlib,os
from pathlib import Path
from unittest.mock import patch
from django.test import SimpleTestCase
from .modules.core import Invalid,text,number,integer,date,timestamp
from .modules.logformat import parse_log
from .updater import install_release,version

class ValidationTests(SimpleTestCase):
    def test_numeric_date_and_text_boundaries(self):
        for value in [True,None,'bad',float('nan'),float('inf'),-1]:
            with self.subTest(value=value),self.assertRaises(Invalid):number(value,'score')
        with self.assertRaises(Invalid):integer(1.2,'score')
        for value in ['',None,'x'*301]:
            with self.subTest(value=value),self.assertRaises(Invalid):text(value)
        for value in ['bad',None]:
            with self.subTest(value=value),self.assertRaises(Invalid):date(value)
        for value in ['2026-01-01T00:00:00','bad',None]:
            with self.subTest(value=value),self.assertRaises(Invalid):timestamp(value)
        self.assertEqual(timestamp('2026-01-01T12:00:00+12:00'),'2026-01-01T00:00:00+00:00')
    def test_log_rejects_malformed_or_ambiguous_events(self):
        for content in ['', 'missing', '[25:00:00] A has killed B from C','[01:00:00] A waved','[01:00:00] A has killed B','[01:00:00]  has killed B from C','[01:00:02] A has killed B from C\n[01:00:01] A has killed B from C']:
            with self.subTest(content=content),self.assertRaises(Invalid):parse_log(content,'2026-09-01')
        with self.assertRaises(Invalid):parse_log('[01:00:00] A has killed B from C','2026-09-01','')
        self.assertEqual(len(parse_log('\n[01:00:00] A has killed B from C\n','2026-09-01')),1)
    def test_update_rollback_preserves_existing_install(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);dest=root/'installed';dest.mkdir();(dest/'release.json').write_text('{"version":"1.0.0"}');(dest/'original').write_text('keep')
            archive=root/'release.zip'
            with zipfile.ZipFile(archive,'w') as bundle:bundle.writestr('new.py','new')
            manifest=root/'release.json';manifest.write_text(json.dumps({'version':'2.0.0','archive':'release.zip','sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}))
            replace=os.replace
            def fail_stage(src,dst):
                if Path(src).name=='stage':raise OSError('simulated failure')
                return replace(src,dst)
            with patch('guilds.updater.os.replace',side_effect=fail_stage),self.assertRaises(OSError):install_release(manifest,dest)
            self.assertEqual((dest/'original').read_text(),'keep');self.assertFalse((dest/'new.py').exists())
            self.assertEqual(install_release(manifest,dest)['installed'],'2.0.0')
            self.assertFalse(install_release(manifest,dest)['available'])
        with self.assertRaises(ValueError):version('invalid')
    def test_wsgi_and_asgi_entrypoints(self):
        from config.wsgi import application as wsgi
        from config.asgi import application as asgi
        self.assertTrue(callable(wsgi));self.assertTrue(callable(asgi))
