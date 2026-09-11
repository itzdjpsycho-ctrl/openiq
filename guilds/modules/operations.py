"""Scheduled work and configuration workflows, all local until delivery is enabled."""
from datetime import timedelta
from zoneinfo import ZoneInfo
from .core import *
from .community import preview
from .analytics import calculate

def handle(g,action,p,role,user):
    require(role)
    if action=='schedule':
        require(role,'owner');kind=choice(p['kind'],['weekly','sync'],'schedule')
        g.config[kind]={**g.config.get(kind,{}),'enabled':bool(p.get('enabled',True)),'weekday':integer(p.get('weekday',0),'weekday',0,6),'hour':integer(p.get('hour',20),'hour',0,23),'timezone':text(p.get('timezone','Pacific/Auckland')),'channel':str(p.get('channel','preview'))}
        try:ZoneInfo(g.config[kind]['timezone'])
        except Exception:raise Invalid('Invalid timezone')
        g.save();return g.config[kind]
    if action in ['tick','catchup']:
        from .community import handle as community
        community(g,'run_due',{},role,user)
        at=datetime.fromisoformat(timestamp(p.get('at',now())))
        days=integer(p.get('days',14 if action=='catchup' else 0),'lookback',0,90)
        count=0
        from .events import handle as events
        for event in rows(g,'event'):
            if event.data.get('recurrence_days') and not event.data.get('next_event') and event.data['at']<=at.isoformat():
                events(g,'next',{'event':event.key},role,user); count+=1
        for kind in ['weekly','sync']:
            config=g.config.get(kind,{})
            if not config.get('enabled'):continue
            local=at.astimezone(ZoneInfo(config.get('timezone','Pacific/Auckland')))
            for offset in range(days+1):
                day=local.date()-timedelta(days=offset)
                if day.weekday()!=config.get('weekday',0) or (offset==0 and local.hour<config.get('hour',20)):continue
                key=kind+':'+day.isoformat()
                if Record.objects.filter(guild=g,kind='job',key=key).exists():continue
                if kind=='weekly':
                    start=(day-timedelta(days=7)).isoformat();end=day.isoformat();wars=[w for w in rows(g,'war') if start<w.data['date']<=end]
                    preview(g,key,f'{g.name}: {len(wars)} wars for week ending {end}.',config.get('channel','preview'))
                    status='previewed'
                else:
                    names=g.config.get('sync_fixture')
                    if config.get('url'):
                        from .integrations import fetch_roster
                        try:names=fetch_roster(config['url'])
                        except Exception as exc:
                            save(g,'job',{'type':kind,'at':at.isoformat(),'status':'source_error','message':str(exc)},key);count+=1;continue
                    if names:
                        from .roster import handle as roster
                        roster(g,'sync',{'names':names},role,user);status='fixture_synced'
                    else:status='needs_roster_source'
                save(g,'job',{'type':kind,'at':at.isoformat(),'status':status},key);count+=1
        return {'processed':count}
    if action=='recruitment_form':
        require(role,'owner');return public(save(g,'recruitment_form',{'title':text(p['title']),'questions':p.get('questions',[]),'channel':str(p.get('channel','preview'))},p.get('id')))
    if action=='ticket_category':
        require(role,'owner');return public(save(g,'ticket_category',{'name':text(p['name']),'staff_role':str(p.get('staff_role',''))},p.get('id')))
    if action=='welcome_role':
        member=get(g,'member',p['member']);allowed=g.config.get('welcome',{}).get('roles',['Raider','Social']);selected=choice(p['role'],allowed,'welcome role')
        member.data.setdefault('community_roles',[])
        if selected not in member.data['community_roles']:member.data['community_roles'].append(selected)
        member.save();return public(member)
    if action=='challenge':
        opponent=get(g,'member',p['opponent']);from .community import handle as community
        mine=community(g,'roll',{},role,user)['roll'];import random
        theirs=random.SystemRandom().randint(1,100)
        return public(save(g,'challenge',{'challenger':user.username,'opponent':opponent.data['name'],'roll':mine,'opponent_roll':theirs,'winner':user.username if mine>theirs else opponent.data['name'] if theirs>mine else 'Draw','mode':'local simulated opponent'}))
    raise Invalid('Unknown operations action')
