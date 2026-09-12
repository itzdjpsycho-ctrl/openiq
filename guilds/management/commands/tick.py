from django.core.management.base import BaseCommand
from guilds.models import Guild,Access
from guilds.services import execute
import os
import time
from guilds.models import Outbox,Record
from guilds.delivery import deliver
class Command(BaseCommand):
    help='Process scheduled work once; deliver queued messages only when explicitly enabled.'
    def handle(self,*args,**options):
        for g in Guild.objects.all():
            owner=Access.objects.filter(guild=g,role='owner').select_related('user').first()
            if owner:self.stdout.write(str(execute(owner.user,g.pk,'operations','tick',{})))
        if os.getenv('ENABLE_DISCORD_DELIVERY')!='1':return
        attempts=0
        for item in Outbox.objects.filter(status='preview').order_by('pk').iterator():
            retry=Record.objects.filter(guild=item.guild,kind='delivery_retry',key=str(item.pk)).first()
            if retry and retry.data.get('next_attempt',0)>time.time():continue
            attempts+=1
            if attempts>100:break
            try:
                result=deliver(item,enabled=True,queued=True)
                self.stdout.write(f'Outbox {item.pk}: {result["status"]}')
                if result['status']=='sent' and item.key.startswith(f'{item.guild_id}:reminder:'):
                    reminder=Record.objects.filter(guild=item.guild,kind='reminder',key=item.key.split(':',2)[2]).first()
                    if reminder:reminder.data['status']='sent';reminder.save()
            except Exception:
                self.stderr.write(f'Outbox {item.pk}: delivery failed; retry scheduled. Inspect Discord permissions and delivery records.')
