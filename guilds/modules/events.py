from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import re
from urllib.parse import urlparse
from .core import *

def reconcile(data):
    for team in data['teams']:
        candidates=sorted([s for s in data.get('signups',[]) if s['team']==team['name']],key=lambda s:s['at'])
        for i,s in enumerate(candidates): s['waitlisted']=i>=team['capacity']

def handle(g,action,p,role,user):
    if action=='signup':
        e=get(g,'event',p['event']); owner_or_self(g,role,user,p['member'])
        if e.data.get('locked') or e.data.get('archived'): raise Invalid('Event is locked or archived')
        team=p.get('team','')
        if team and team not in [t['name'] for t in e.data['teams']]: raise Invalid('Unknown team')
        existing=next((s for s in e.data.get('signups',[]) if s['member']==p['member']),None)
        e.data['signups']=[s for s in e.data.get('signups',[]) if s['member']!=p['member']]
        if team: e.data['signups'].append({'member':p['member'],'team':team,'at':existing['at'] if existing and existing['team']==team else now()})
        reconcile(e.data); e.save(); return public(e)
    require(role)
    if action=='save':
        old=get(g,'event',p['id']).data if p.get('id') else {'signups':[]}
        teams=p.get('teams',old.get('teams',[]))
        if not isinstance(teams,list) or not teams: raise Invalid('Add at least one team')
        if len(teams)>24:raise Invalid('Use at most 24 teams per Discord signup card')
        for t in teams:
            t['name']=text(t['name'],'team name',80); t['capacity']=integer(t['capacity'],'capacity',1,1000)
            t['group']=text(t['group'],'team group',80) if t.get('group') else ''
        if len({t['name'] for t in teams})!=len(teams): raise Invalid('Team names must be unique')
        if any(s['team'] not in [t['name'] for t in teams] for s in old.get('signups',[])): raise Invalid('Move existing signups before removing a team')
        tz=p.get('timezone',old.get('timezone','Pacific/Auckland'))
        try: ZoneInfo(tz)
        except (ZoneInfoNotFoundError,TypeError): raise Invalid('Unknown timezone')
        d={**old,'title':text(p.get('title',old.get('title'))),'type':choice(p.get('type',old.get('type','Node')),['Node','Siege','Practice','Custom'],'event type'),'at':timestamp(p.get('at',old.get('at'))),'timezone':tz,'teams':teams,'locked':bool(p.get('locked',old.get('locked',False))),'archived':bool(p.get('archived',old.get('archived',False))),'recurrence_days':integer(p.get('recurrence_days',old.get('recurrence_days',0)),'repeat days',0,365)}
        for key in ['image','accent','mention_roles']:
            d[key]=p.get(key,old.get(key,''))
        if d['image']:
            image=urlparse(text(d['image'],'image URL',2000))
            if image.scheme!='https' or not image.hostname or image.username:raise Invalid('Use an HTTPS image URL')
        if d['accent'] and not re.fullmatch(r'#[0-9a-fA-F]{6}',d['accent']):raise Invalid('Accent must be a six-digit hex color')
        reconcile(d)
        if d['archived'] and not old.get('pity_awarded'):
            for signup in d['signups']:
                if signup.get('waitlisted'):
                    member=get(g,'member',signup['member']); member.data['pity_points']=member.data.get('pity_points',0)+1; member.save()
            d['pity_awarded']=True
        return public(save(g,'event',d,p.get('id')))
    if action=='share':
        e=get(g,'event',p['event']); e.data['alliance_share']=bool(p.get('enabled',True)); e.data['share_token']=e.data.get('share_token') or ident(); e.save(); return public(e)
    if action=='template':
        e=get(g,'event',p['event']); return public(save(g,'template',{'name':text(p['name']),'event':{k:v for k,v in e.data.items() if k!='signups'}}))
    if action=='from_template':
        t=get(g,'template',p['template']); return handle(g,'save',{**t.data['event'],'at':p['at'],'locked':False,'archived':False},role,user)
    if action=='next':
        e=get(g,'event',p['event'])
        if e.data.get('next_event'): return public(get(g,'event',e.data['next_event']))
        days=e.data.get('recurrence_days',0)
        if not days: raise Invalid('No recurrence configured')
        local=datetime.fromisoformat(e.data['at']).astimezone(ZoneInfo(e.data['timezone']))
        result=handle(g,'save',{**e.data,'at':(local+timedelta(days=days)).isoformat(),'locked':False,'archived':False},role,user)
        e.data['next_event']=result['id']; e.save(); return result
    raise Invalid('Unknown event action')
