"""Permission payload and idempotent update contracts; all HTTP is mocked."""
import io
from unittest.mock import Mock,patch
import httpx
from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from .models import Guild,Access,Record
from .services import execute
from .discord_tickets import synchronize,plan,VIEW,SEND
from .modules.core import Invalid,get

class DiscordTicketTests(TestCase):
    def setUp(self):
        self.owner=User.objects.create_user('owner');self.member=User.objects.create_user('member')
        self.g=Guild.objects.create(name='Guild',server_id='100',config={'tickets':{'bot_user_id':'200','staff_role':'300','category_id':'400'}})
        Access.objects.create(guild=self.g,user=self.owner,role='owner');Access.objects.create(guild=self.g,user=self.member,role='member')
        m=execute(self.owner,self.g.pk,'roster','save',{'name':'Alpha'})
        execute(self.owner,self.g.pk,'roster','link',{'member':m['id'],'user_id':self.member.pk,'discord_id':'500'})
        self.ticket=execute(self.member,self.g.pk,'community','ticket',{'subject':'Help','text':'Question'})['id']
    def test_preview_has_private_acl_and_never_connects(self):
        with patch('httpx.request') as network:
            result=synchronize(self.owner,self.g,self.ticket);network.assert_not_called()
        self.assertEqual(result['mode'],'preview');self.assertIn('permission_overwrites',execute(self.owner,self.g.pk,'community','ticket_preview',{'ticket':self.ticket})['text']);acl=result['channel']['permission_overwrites']
        self.assertEqual(acl[0]['deny'],str(VIEW));self.assertEqual(acl[1]['id'],'500');self.assertEqual(result['channel']['parent_id'],'400')
        out=io.StringIO();call_command('ticket_channel',self.ticket,guild=self.g.pk,user='owner',stdout=out)
        self.assertIn('preview',out.getvalue())
        with self.assertRaises(PermissionDenied):synchronize(self.member,self.g,self.ticket)
    def test_category_override_and_missing_configuration(self):
        execute(self.owner,self.g.pk,'operations','ticket_category',{'name':'General','staff_role':'600'})
        self.g.config['tickets'].pop('category_id');result=plan(self.g,get(self.g,'ticket',self.ticket))
        self.assertNotIn('parent_id',result['channel']);self.assertEqual(result['channel']['permission_overwrites'][2]['id'],'600')
        self.g.server_id='invalid'
        with self.assertRaises(Invalid):synchronize(self.owner,self.g,self.ticket)
    def test_create_update_close_and_delivery_failures(self):
        response=Mock();response.json.return_value={'id':'700'}
        with patch.dict('os.environ',{'ENABLE_DISCORD_DELIVERY':'0'}),self.assertRaises(Invalid):synchronize(self.owner,self.g,self.ticket,True)
        with patch.dict('os.environ',{'ENABLE_DISCORD_DELIVERY':'1','DISCORD_BOT_TOKEN':'test'}),patch('httpx.request',return_value=response) as request:
            synchronize(self.owner,self.g,self.ticket,True)
            self.assertEqual(request.call_args_list[0].args[0],'POST');self.assertEqual(request.call_args_list[1].args[0],'POST')
            request.reset_mock();execute(self.owner,self.g.pk,'community','close_ticket',{'ticket':self.ticket})
            synchronize(self.owner,self.g,self.ticket,True)
            self.assertEqual(request.call_args_list[0].args[0],'PATCH');self.assertEqual(request.call_args_list[1].args[0],'PATCH')
            payload=request.call_args_list[0].kwargs['json'];self.assertEqual(payload['permission_overwrites'][1]['deny'],str(SEND));self.assertTrue(payload['name'].startswith('closed-'))
            request.side_effect=httpx.ConnectError('offline')
            with self.assertRaises(httpx.ConnectError):synchronize(self.owner,self.g,self.ticket,True)
            self.assertEqual(Record.objects.filter(kind='ticket_channel').count(),1)
    def test_everyone_role_is_rejected_and_long_transcript_is_preserved(self):
        self.g.config['tickets']['staff_role']=self.g.server_id
        with self.assertRaises(Invalid):plan(self.g,get(self.g,'ticket',self.ticket))
        self.g.config['tickets']['staff_role']='300'
        execute(self.member,self.g.pk,'community','reply',{'ticket':self.ticket,'text':'x'*4000})
        response=Mock();response.json.return_value={'id':'700'}
        with patch.dict('os.environ',{'ENABLE_DISCORD_DELIVERY':'1','DISCORD_BOT_TOKEN':'test'}),patch('httpx.request',return_value=response) as request:
            synchronize(self.owner,self.g,self.ticket,True)
        messages=[call.kwargs['json']['content'] for call in request.call_args_list if 'content' in call.kwargs['json']]
        self.assertEqual(''.join(messages),'Help\nQuestion\nmember: '+'x'*4000);self.assertTrue(all(len(m)<=1900 for m in messages))
