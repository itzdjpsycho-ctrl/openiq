"""Remote contracts are tested with controlled responses, never live credentials."""
import os,time,io
from unittest.mock import Mock,patch
import httpx
from django.test import TestCase
from django.contrib.auth.models import User
from .models import Guild,Access
from .modules.core import Invalid
from .modules.integrations import fetch_roster,ocr,roster_html
from .discord_auth import synchronize

HTML='<a href="/Adventure/Profile?name=A">Alpha</a><a href="/Adventure/Profile?name=A">Alpha</a>'
class AdapterTests(TestCase):
    def test_roster_fetch_allowlist_rate_limit_and_empty_page(self):
        response=Mock(status_code=200,text=HTML)
        with patch('httpx.get',return_value=response) as request:
            self.assertEqual(fetch_roster('https://www.naeu.playblackdesert.com/Adventure/Guild'),['Alpha'])
            self.assertFalse(request.call_args.kwargs['follow_redirects'])
            response.status_code=429
            with self.assertRaises(Invalid):fetch_roster('https://www.naeu.playblackdesert.com/Adventure/Guild')
            response.status_code=200;response.text='<html>No roster</html>'
            with self.assertRaises(Invalid):fetch_roster('https://www.naeu.playblackdesert.com/Adventure/Guild')
        for url in ['https://evil.example/','https://user@www.naeu.playblackdesert.com/','https://www.naeu.playblackdesert.com:8080/']:
            with self.subTest(url=url),self.assertRaises(Invalid):fetch_roster(url)
        self.assertEqual(roster_html('<span>Ignored</span>'+HTML),['Alpha'])
    def test_ocr_validation_and_normalization(self):
        from PIL import Image
        data=io.BytesIO();Image.new('RGB',(20,20),'white').save(data,format='PNG')
        with patch('pytesseract.image_to_string',return_value='Alpha') as engine:
            self.assertEqual(ocr(data.getvalue()),'Alpha');self.assertEqual(engine.call_args.args[0].mode,'L')
        with self.assertRaises(Invalid):ocr(b'bad image')
        with self.assertRaises(Invalid):ocr(bytes(10*1024*1024+1))
        with patch('pytesseract.image_to_string',side_effect=RuntimeError('timeout')),self.assertRaises(Invalid):ocr(data.getvalue())
    def test_oauth_begin_success_callback_and_replay_rejection(self):
        token=Mock();token.json.return_value={'access_token':'test','refresh_token':'refresh','expires_in':3600}
        profile=Mock();profile.json.return_value={'id':'123'}
        with patch.dict(os.environ,{'DISCORD_CLIENT_ID':'id','DISCORD_CLIENT_SECRET':'secret'}):
            result=self.client.get('/auth/discord/');self.assertEqual(result.status_code,302)
            state=self.client.session['oauth_state']['value']
            with patch('httpx.post',return_value=token),patch('httpx.get',return_value=profile),patch('guilds.discord_auth.synchronize') as sync:
                response=self.client.get('/auth/discord/callback/',{'state':state,'code':'code'})
                self.assertEqual(response.status_code,302);sync.assert_called_once()
                self.assertFalse(User.objects.get(username='discord_123').has_usable_password())
            self.assertEqual(self.client.get('/auth/discord/callback/',{'state':state,'code':'code'}).status_code,400)
    def test_oauth_remote_failure_does_not_authenticate(self):
        session=self.client.session;session['oauth_state']={'value':'test','at':time.time()};session.save()
        with patch('httpx.post',side_effect=httpx.ConnectError('offline')):
            self.assertEqual(self.client.get('/auth/discord/callback/',{'state':'test','code':'code'}).status_code,400)
        self.assertNotIn('_auth_user_id',self.client.session)
    def test_synchronize_grants_and_revokes_roles_atomically(self):
        user=User.objects.create_user('discord_user');g=Guild.objects.create(name='Guild',server_id='123',config={'roles':{'admin':['42']}})
        servers=Mock();servers.json.return_value=[{'id':'123'}]
        member=Mock(status_code=200);member.json.return_value={'roles':['42']}
        client=Mock();client.get.side_effect=[servers,member]
        with patch('httpx.Client') as factory:
            factory.return_value.__enter__.return_value=client;synchronize(user,'test')
        self.assertEqual(Access.objects.get(user=user,guild=g).role,'admin')
        servers.json.return_value=[];client.get.side_effect=[servers]
        with patch('httpx.Client') as factory:
            factory.return_value.__enter__.return_value=client;synchronize(user,'test')
        self.assertFalse(Access.objects.filter(user=user,guild=g).exists())
    def test_role_refresh_failure_logs_out(self):
        user=User.objects.create_user('discord_user');self.client.force_login(user)
        session=self.client.session;session['discord_tokens']={'access':'test','refresh':'refresh','expires':time.time()+5000};session['discord_checked']=0;session.save()
        with patch('guilds.discord_auth.synchronize',side_effect=httpx.ConnectError('offline')):
            response=self.client.get('/');self.assertEqual(response.status_code,302)
        self.assertNotIn('_auth_user_id',self.client.session)
    def test_expired_token_refresh_success(self):
        user=User.objects.create_user('discord_user');self.client.force_login(user)
        session=self.client.session;session['discord_tokens']={'access':'old','refresh':'refresh','expires':0};session['discord_checked']=0;session.save()
        response=Mock();response.json.return_value={'access_token':'new','expires_in':3600}
        with patch('httpx.post',return_value=response),patch('guilds.discord_auth.synchronize') as sync:
            self.assertEqual(self.client.get('/').status_code,200);sync.assert_called_once_with(user,'new')
        self.assertEqual(self.client.session['discord_tokens']['access'],'new')
