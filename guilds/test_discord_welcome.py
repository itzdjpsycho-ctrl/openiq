from unittest.mock import Mock,patch
import httpx
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from .models import Guild,Access,Record
from .services import execute
from .modules.core import Invalid,get
from .discord_welcome import choose,components
from .discord_components import process

class WelcomeTests(TestCase):
    def setUp(self):
        self.owner=User.objects.create_user('owner');self.user=User.objects.create_user('member')
        self.g=Guild.objects.create(name='Guild',server_id='100',config={'welcome':{'roles':['Raider','Social'],'role_ids':{'Raider':'200','Social':'300'}}})
        Access.objects.create(guild=self.g,user=self.owner,role='owner');Access.objects.create(guild=self.g,user=self.user,role='member')
        self.m=execute(self.owner,self.g.pk,'roster','save',{'name':'Alpha'})['id']
        execute(self.owner,self.g.pk,'roster','link',{'member':self.m,'user_id':self.user.pk,'discord_id':'400'})
    def test_card_buttons_and_local_self_selection(self):
        card=execute(self.owner,self.g.pk,'community','welcome',{'member':self.m,'message':'Welcome aboard'})
        buttons=Record.objects.get(kind='message_components',key=str(card['id'])).data['components']
        with patch('httpx.put') as network:
            result=process(self.user,buttons[0]['components'][0]['custom_id']);network.assert_not_called()
        self.assertEqual(result['community_roles'],['Raider']);self.assertEqual(result['delivery'],'local')
        self.assertEqual(choose(self.user,self.g,self.m,'200')['community_roles'],['Raider'])
    def test_only_linked_member_or_officer_can_choose(self):
        other=execute(self.owner,self.g.pk,'roster','save',{'name':'Beta'})['id']
        with self.assertRaises(PermissionDenied):choose(self.user,self.g,other,'200')
        with self.assertRaises(Invalid):choose(self.user,self.g,self.m,'999')
        self.g.config['welcome']['roles']=['Social']
        with self.assertRaises(Invalid):choose(self.user,self.g,self.m,'200')
        self.assertEqual(components(Guild(name='Empty'),get(self.g,'member',self.m)),[])
    def test_remote_role_grant_and_failure_do_not_fake_local_success(self):
        with patch.dict('os.environ',{'ENABLE_DISCORD_DELIVERY':'0'}),self.assertRaises(Invalid):choose(self.user,self.g,self.m,'200',True)
        with patch.dict('os.environ',{'ENABLE_DISCORD_DELIVERY':'1','DISCORD_BOT_TOKEN':'test'}),patch('httpx.put',side_effect=httpx.ConnectError('offline')),self.assertRaises(httpx.ConnectError):choose(self.user,self.g,self.m,'200',True)
        self.assertNotIn('community_roles',get(self.g,'member',self.m).data)
        with patch.dict('os.environ',{'ENABLE_DISCORD_DELIVERY':'1','DISCORD_BOT_TOKEN':'test'}),patch('httpx.put',return_value=Mock()) as request:
            result=choose(self.user,self.g,self.m,'200',True)
            self.assertTrue(request.call_args.args[0].endswith('/guilds/100/members/400/roles/200'));self.assertEqual(result['delivery'],'Discord')
