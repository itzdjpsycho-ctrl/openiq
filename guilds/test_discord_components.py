from django.test import TestCase
from django.contrib.auth.models import User
from .models import Guild,Access,Record
from .services import execute
from .discord_components import event_components,process
from .modules.core import Invalid


class PersistentComponentTests(TestCase):
    def test_signed_cards_stale_layout_and_durable_replay_receipts(self):
        user=User.objects.create_user('discord_1');guild=Guild.objects.create(name='Cards')
        Access.objects.create(guild=guild,user=user,role='owner')
        member=execute(user,guild.pk,'roster','save',{'name':'Alpha'})
        execute(user,guild.pk,'roster','link',{'member':member['id'],'user_id':user.pk})
        event=execute(user,guild.pk,'events','save',{'title':'War','at':'2026-09-20T00:00:00Z','teams':[{'name':'Front','capacity':1},{'name':'Back','capacity':1}]})
        record=Record.objects.get(guild=guild,kind='event',key=event['id'])
        card=event_components(guild,record)[0]['components'][0]['custom_id']
        self.assertLessEqual(len(card),100)
        process(user,card,True,interaction_id='123')
        self.assertEqual(process(user,card,True,interaction_id='123'),{'duplicate':True})
        withdrawal=event_components(guild,record)[0]['components'][-1]['custom_id']
        with self.assertRaises(Invalid):process(user,withdrawal,True,interaction_id='123')
        process(user,withdrawal,True,interaction_id='124')
        # A fresh caller/reloaded record still recognizes the receipt after other actions.
        self.assertEqual(process(User.objects.get(pk=user.pk),card,True,interaction_id='123'),{'duplicate':True})
        self.assertEqual(Record.objects.get(pk=record.pk).data['signups'],[])
        for invalid in [card[:-1]+'x',f'signup:{guild.pk}:{record.key}:0','signup:bad:key:0','junk']:
            with self.assertRaises(Invalid):process(user,invalid,True)
        execute(user,guild.pk,'events','save',{'id':record.key,'teams':[{'name':'Back','capacity':1},{'name':'Front','capacity':1}]})
        with self.assertRaises(Invalid):process(user,card,True)
        execute(user,guild.pk,'events','save',{'id':record.key,'locked':True})
        record.refresh_from_db();self.assertTrue(event_components(guild,record)[0]['components'][0]['disabled'])
        with self.assertRaises(Invalid):process(user,event_components(guild,record)[0]['components'][0]['custom_id'],True)
        self.client.force_login(user)
        self.assertNotIn('bot_receipt',self.client.get(f'/api/{guild.pk}/state/').json()['records'])
