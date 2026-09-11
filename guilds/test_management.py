"""CLI workflows run locally; bot connection and live sniffing stay mocked."""
import io,json,tempfile
from pathlib import Path
from unittest.mock import Mock,patch
from django.test import TestCase
from django.core.management import call_command,CommandError
from django.contrib.auth.models import User
from .models import Guild,Access,Outbox,Record
from .services import execute
ROOT=Path(__file__).resolve().parents[1]
class ManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user=User.objects.create_user('cli');cls.g=Guild.objects.create(name='CLI');Access.objects.create(guild=cls.g,user=cls.user,role='owner')
    def call(self,name,*args,**kwargs):
        out=io.StringIO();call_command(name,*args,stdout=out,stderr=io.StringIO(),**kwargs);return out.getvalue()
    def test_local_command_tick_and_delivery_preview(self):
        self.assertEqual(json.loads(self.call('local_command','guildstats',guild=self.g.pk,user='cli'))['wars'],0)
        self.call('tick')
        item=Outbox.objects.create(guild=self.g,key='cli',text='Message')
        self.assertIn('preview',self.call('deliver',str(item.pk)))
        with self.assertRaises(CommandError):self.call('deliver','999999')
    def test_capture_once_and_offline_packet_command(self):
        session=execute(self.user,self.g.pk,'live','start',{'title':'Capture'})
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/'events.jsonl';file.write_text(json.dumps({'id':'1','at':'2026-09-01T20:00:00Z','kind':'kill','player':'Alpha','target':'Enemy'})+'\n')
            self.call('capture',str(file),session=session['id'],guild=self.g.pk,user='cli',once=True)
            self.assertEqual(len(Record.objects.get(kind='session').data['events']),1)
            output=Path(temp)/'decoded.jsonl'
            self.call('packet_capture',calibration=str(ROOT/'fixtures/calibration-historical.json'),pcap=str(ROOT/'fixtures/combat-synthetic.pcap'),output=str(output))
            self.assertEqual(len(output.read_text().splitlines()),2)
    def test_release_check_and_install_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.call('release_capture',output=str(root/'release'),release_version='1.0.0')
            manifest=str(root/'release/manifest.json');destination=str(root/'installed')
            self.assertIn("'available': True",self.call('update_capture',manifest,destination))
            self.call('update_capture',manifest,destination,install=True)
            self.assertTrue((root/'installed/scripts/capture_desktop.py').exists())
    def test_bot_command_registry_never_connects_in_check_mode(self):
        with patch('discord.Client.run') as connect:
            self.assertIn('53 commands',self.call('runbot',check=True));connect.assert_not_called()
        with patch.dict('os.environ',{'DISCORD_BOT_TOKEN':'','ENABLE_DISCORD_DELIVERY':'0'}),self.assertRaises(CommandError):self.call('runbot')
    def test_scheduler_runs_once_and_handles_failure(self):
        for failure in [None,RuntimeError('failure')]:
            stop=Mock();stop.is_set.side_effect=[False,True]
            with patch('guilds.management.commands.scheduler.threading.Event',return_value=stop),patch('guilds.management.commands.scheduler.signal.signal'),patch('guilds.management.commands.scheduler.call_command',side_effect=failure) as tick:
                self.call('scheduler',interval=0);tick.assert_called_once();stop.wait.assert_called_once_with(1)
    def test_seed_is_idempotent(self):
        self.call('seed_demo');counts=(Guild.objects.count(),Record.objects.count())
        self.call('seed_demo');self.assertEqual(counts,(Guild.objects.count(),Record.objects.count()))
    def test_bot_gateway_command_and_component_contracts(self):
        from unittest.mock import AsyncMock
        from asgiref.sync import async_to_sync
        import discord
        self.g.server_id='123';self.g.save()
        with patch.dict('os.environ',{'DISCORD_BOT_TOKEN':'test','ENABLE_DISCORD_DELIVERY':'1'}),patch('discord.Client.run',autospec=True) as connect:
            self.call('runbot',sync=True)
        bot=connect.call_args.args[0]
        with patch.object(bot.tree,'sync',new_callable=AsyncMock) as sync:
            async_to_sync(bot.setup_hook)();sync.assert_awaited_once()
        interaction=Mock();interaction.guild_id=123;interaction.channel_id=456;interaction.guild.owner_id=7;interaction.user.id=7;interaction.user.roles=[];interaction.user.guild_permissions.value=8
        interaction.response.defer=AsyncMock();interaction.response.send_message=AsyncMock();interaction.followup.send=AsyncMock()
        command=bot.tree.get_command('guildstats')
        async_to_sync(command.callback)(interaction)
        self.assertIn('"wars": 0',interaction.followup.send.call_args.args[0])
        user=User.objects.get(username='discord_7')
        m=execute(self.user,self.g.pk,'roster','save',{'name':'Alpha'})
        execute(self.user,self.g.pk,'roster','link',{'member':m['id'],'user_id':user.pk})
        e=execute(self.user,self.g.pk,'events','save',{'title':'War','at':'2026-09-01T00:00:00Z','teams':[{'name':'Front','capacity':1}]})
        interaction.data={'custom_id':f"signup:{self.g.pk}:{e['id']}:0"}
        async_to_sync(bot.on_interaction)(interaction)
        self.assertEqual(interaction.followup.send.call_args.args[0],'Signup updated.')
        interaction.guild_id=999;async_to_sync(bot.on_interaction)(interaction)
        self.assertEqual(interaction.followup.send.call_args.args[0],'Wrong server')
        interaction.guild_id=123
        async_to_sync(command.callback)(interaction,arguments='invalid JSON')
        self.assertIn('Expecting value',interaction.followup.send.call_args.args[0])
        async_to_sync(command.callback)(interaction,guild_name='missing')
        self.assertIn('Specify guild_name',interaction.followup.send.call_args.args[0])
        self.g.config={'channels':{'bot':'999'}};self.g.save()
        async_to_sync(command.callback)(interaction)
        self.assertIn('configured command channel',interaction.followup.send.call_args.args[0])
        interaction.guild.owner_id=999;interaction.user.guild_permissions.value=0
        async_to_sync(command.callback)(interaction)
        self.assertIn('do not grant access',interaction.followup.send.call_args.args[0])
        async_to_sync(bot.on_interaction)(interaction)
        self.assertEqual(interaction.followup.send.call_args.args[0],'No guild access')
        interaction.data={'custom_id':'irrelevant'};async_to_sync(bot.on_interaction)(interaction)
        interaction.guild=None;async_to_sync(command.callback)(interaction)
        self.assertIn('server',interaction.response.send_message.call_args.args[0])
    def test_live_packet_selection_is_mocked_and_errors_are_reported(self):
        with patch('scapy.sendrecv.sniff') as sniff:
            self.call('packet_capture',calibration=str(ROOT/'fixtures/calibration-historical.json'),interfaces=['test0'],seconds=1)
            self.assertEqual(sniff.call_args.kwargs['iface'],['test0'])
        with self.assertRaises(CommandError):self.call('packet_capture',calibration=str(ROOT/'fixtures/calibration-historical.json'),pcap='/does/not/exist')
    def test_capture_interrupt_exits_cleanly(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/'empty.jsonl';file.write_text('')
            with patch('guilds.management.commands.capture.time.sleep',side_effect=KeyboardInterrupt):
                self.assertIn('Capture stopped',self.call('capture',str(file),session='unused',guild=self.g.pk,user='cli'))

    def test_offline_packet_command_stdout_contract(self):
        output=self.call('packet_capture',calibration=str(ROOT/'fixtures/calibration-historical.json'),pcap=str(ROOT/'fixtures/combat-synthetic.pcap'))
        self.assertEqual([json.loads(line)['kind'] for line in output.splitlines()],['kill','death'])
