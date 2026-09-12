from django.test import TestCase
from django.contrib.auth.models import User
from .models import Guild,Access,Record,Outbox
from .services import execute
from .modules.core import Invalid


class EventCardTests(TestCase):
    def test_published_card_tracks_signups_edits_and_archive(self):
        user=User.objects.create_user('officer');guild=Guild.objects.create(name='Event guild',config={'channels':{'events':'123'}})
        Access.objects.create(user=user,guild=guild,role='owner')
        def run(command,payload):return execute(user,guild.pk,'commands','run',{'command':command,'arguments':payload})
        event=run('event create',{'title':'War','at':'2026-09-20T00:00:00Z','teams':[{'name':'Front','capacity':1}],'image':'https://example.com/card.png','accent':'#123456'})
        self.assertFalse(Outbox.objects.exists())
        card=run('event post',{'event':event['id']});item=Outbox.objects.get(pk=card['id'])
        with self.assertRaises(Invalid):run('event signup',{'event':event['id'],'team':'Front'})
        member=execute(user,guild.pk,'roster','save',{'name':'Alpha'})
        execute(user,guild.pk,'roster','link',{'member':member['id'],'user_id':user.pk})
        item.status='sent';item.save()
        run('event signup',{'event':event['id'],'team':'Front'})
        item.refresh_from_db();self.assertIn('Alpha',item.text);self.assertEqual(item.status,'preview')
        run('event edit',{'id':event['id'],'locked':True})
        item.refresh_from_db();self.assertIn('Locked',item.text)
        payload=Record.objects.get(kind='message_components',key=str(item.pk)).data
        self.assertTrue(payload['components'][0]['components'][0]['disabled'])
        self.assertEqual(payload['embeds'][0]['color'],0x123456)
        from unittest.mock import patch,Mock
        from .delivery import deliver
        response=Mock();response.json.return_value={'id':'999'}
        with patch.dict('os.environ',{'DISCORD_BOT_TOKEN':'test','ENABLE_DISCORD_DELIVERY':'1'}),patch('httpx.request',return_value=response) as request:
            deliver(item,True)
        self.assertEqual(request.call_args.kwargs['json']['embeds'][0]['color'],0x123456)
        # Image-only changes also enqueue an update even when message text is unchanged.
        item.status='sent';item.save();run('event edit',{'id':event['id'],'image':'https://example.com/new.png'})
        item.refresh_from_db();self.assertEqual(item.status,'preview')
        run('event edit',{'id':event['id'],'archived':True});item.refresh_from_db();self.assertIn('Archived',item.text)
        self.assertEqual(Outbox.objects.count(),1)
        with self.assertRaises(Invalid):run('event create',{'teams':[{'name':str(i),'capacity':1} for i in range(25)]})
