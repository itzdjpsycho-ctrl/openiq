import os
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from guilds.models import Guild,Access,Record
from guilds.modules.core import save,now
from guilds.services import execute

class Command(BaseCommand):
    help='Create isolated demo guilds and three local accounts; never contacts Discord.'
    @transaction.atomic
    def handle(self,*args,**options):
        password=os.getenv('DEMO_PASSWORD','prototype-local-2026')
        users={}
        for name,role in [('demo','owner'),('officer','admin'),('member','member')]:
            user,created=User.objects.get_or_create(username=name)
            if created: user.set_password(password); user.save()
            users[role]=user
        guild,created=Guild.objects.get_or_create(name='Aurora')
        ally,_=Guild.objects.get_or_create(name='Silver Meridian')
        for role,user in users.items(): Access.objects.get_or_create(guild=guild,user=user,defaults={'role':role})
        Access.objects.get_or_create(guild=ally,user=users['owner'],defaults={'role':'owner'})
        if Record.objects.filter(guild=guild,kind='member').exists(): self.stdout.write('Demo already exists; left unchanged.'); return
        user=users['owner']; invoke=lambda m,a,p:execute(user,guild.pk,m,a,p)
        classes=['Warrior','Shai','Guardian','Wizard','Valkyrie','Ranger','Ninja','Sage','Woosa','Maegu','Drakania','Berserker']
        names=['Aster','Juniper','Kestrel','Solstice','Vesper','Rook','Ember','Orion','Willow','Mistral','Nova','Flint']
        ids=[]
        for i,(name,cl) in enumerate(zip(names,classes)):
            m=invoke('roster','save',{'name':name,'class':cl,'joined':'2026-01-01','group':['Frontline','Flex','Backline'][i%3]}); ids.append(m['id'])
            invoke('gear','save',{'member':m['id'],'ap':290+i*2,'aap':292+i*2,'dp':380+i*3})
        invoke('roster','link',{'member':ids[0],'user_id':users['owner'].pk});invoke('roster','link',{'member':ids[1],'user_id':users['member'].pk})
        for i in range(9):
            from datetime import date
            day=(date.today()-timedelta(days=(9-i)*3)).isoformat()
            invoke('wars','save',{'date':day,'type':'Siege' if i%3==0 else 'Node','result':['Win','Win','Loss','Draw'][i%4],'capped':bool(i%2),'alliance_included':True,'participants':[{'member':mid,'kills':15+(i*7+j*11)%90,'deaths':5+(i*3+j*7)%45} for j,mid in enumerate(ids) if (i+j)%7!=0]})
        for group in ['Frontline','Flex','Backline']:invoke('roster','group',{'name':group})
        invoke('roster','note',{'member':ids[0],'text':'Call target swaps early; review positioning in the next practice.'})
        from datetime import datetime,timezone
        event=invoke('events','save',{'title':'Friday · Node War','type':'Node','at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),'teams':[{'name':'Frontline','capacity':4},{'name':'Flex','capacity':3},{'name':'Backline','capacity':4}],'recurrence_days':7})
        for i,mid in enumerate(ids):invoke('events','signup',{'event':event['id'],'member':mid,'team':['Frontline','Flex','Backline'][i%3]})
        invoke('events','template',{'event':event['id'],'name':'Standard node war'})
        invoke('coaching','lead',{'name':'Combat mentors','capacity':3})
        invoke('community','ticket',{'subject':'Practice schedule','text':'Could we run a positioning session before the next siege?'})
        invoke('community','apply',{'family':'SilverFox','answers':'Succession Wizard, 720 GS, available Tuesday and Friday evenings.'})
        invoke('community','weekly',{}); invoke('community','post_event',{'event':event['id']})
        invoke('integrations','streams_fixture',{'streams':[{'handle':'demo_aurora','title':'Demo fixture · Node war preparation','viewers':124,'category':'Nodewar','partner':False},{'handle':'demo_meridian','title':'Demo fixture · Guild practice','viewers':87,'category':'Practice','partner':True}]})
        session=invoke('live','start',{'title':'Aurora vs Moonfall · practice replay'})
        start=datetime.now(timezone.utc)-timedelta(hours=2)
        invoke('live','ingest',{'session':session['id'],'events':[{'id':f'demo-{i}','at':(start+timedelta(seconds=i*23)).isoformat(),'kind':'kill' if i%3 else 'death','player':names[i%12] if i%3 else 'Opponent','target':'Opponent' if i%3 else names[i%12],'guild':['Moonfall','Iron Vow'][i%2],'class':classes[i%12]} for i in range(60)]})
        invoke('live','stop',{'session':session['id']})
        save(guild,'retention',{'at':now(),'members':12})
        self.stdout.write('Demo ready: demo / officer / member. Password from DEMO_PASSWORD, default prototype-local-2026. Start on http://127.0.0.1:8000/')
