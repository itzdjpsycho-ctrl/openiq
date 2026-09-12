import asyncio
import json
from unittest.mock import AsyncMock,Mock
import httpx
from django.core.exceptions import ObjectDoesNotExist,PermissionDenied
from django.test import SimpleTestCase
from .discord_responses import respond,error_message
from .modules.core import Invalid


class ResponseTests(SimpleTestCase):
    def test_readable_private_results_and_nontruncated_files(self):
        interaction=Mock();interaction.followup.send=AsyncMock()
        asyncio.run(respond(interaction,{'wars':2,'teams':['Front'],'status':'saved'}))
        self.assertIn('Wars: 2',interaction.followup.send.call_args.args[0])
        self.assertTrue(interaction.followup.send.call_args.kwargs['ephemeral'])
        asyncio.run(respond(interaction,'@everyone **bold**'))
        self.assertNotIn('@everyone',interaction.followup.send.call_args.args[0])
        asyncio.run(respond(interaction,{}));self.assertEqual(interaction.followup.send.call_args.args[0],'Done.')
        asyncio.run(respond(interaction,[1,2]));self.assertIn('1',interaction.followup.send.call_args.args[0])
        captured=[]
        async def capture(*args,**kwargs):captured.append(json.loads(kwargs['file'].fp.read()))
        interaction.followup.send=AsyncMock(side_effect=capture)
        result={'full':'😀'*1500};asyncio.run(respond(interaction,result));self.assertEqual(captured,[result])
        interaction.followup.send=AsyncMock()
        asyncio.run(respond(interaction,'x'*(8*1024*1024+1)))
        self.assertIn('exceeds',interaction.followup.send.call_args.args[0])

    def test_errors_do_not_expose_internal_details(self):
        self.assertEqual(error_message(Invalid('Choose a team')),'Choose a team')
        for error in [PermissionDenied('secret'),ObjectDoesNotExist('secret'),ValueError('secret'),httpx.ConnectError('secret')]:
            self.assertNotIn('secret',error_message(error))
        with self.assertLogs('guilds.discord_responses',level='ERROR') as logs:
            message=error_message(RuntimeError('password=secret'))
        self.assertIn('reference',message);self.assertNotIn('secret',message+' '.join(logs.output))
