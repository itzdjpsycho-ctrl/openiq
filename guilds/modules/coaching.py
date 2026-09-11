from datetime import datetime, timedelta
from .core import *
from .analytics import calculate

def window(items, config, fallback=7):
    mode=config.get('mode','wars'); size=config.get('size',fallback)
    if mode=='all': return items
    if mode=='wars': return items[-size:]
    today=datetime.now(timezone.utc).date()
    if mode=='days': cutoff=(today-timedelta(days=size)).isoformat(); return [i for i in items if i.get('date',i.get('at',''))[:10]>=cutoff]
    first=today.replace(day=1); previous=first-timedelta(days=1); start=previous.replace(day=1).isoformat();end=first.isoformat()
    return [i for i in items if start<=i.get('date',i.get('at',''))[:10]<end]

def flags(g):
    config=g.config.get('performance',{});
    if not config.get('enabled',True): return []
    result=[]; lookup={m.key:m for m in rows(g,'member')}; assignments=rows(g,'assignment')
    for s in calculate(g)['members']:
        m=lookup[s['id']].data
        if not m.get('active') or m.get('exception'): continue
        if (datetime.now(timezone.utc).date()-datetime.fromisoformat(m['joined']).date()).days<config.get('grace_days',7): continue
        if any(v['start']<=now()[:10]<=v['end'] for v in m.get('vacations',[])): continue
        recent=window(s['timeline'],config.get('kdr_window',{}),config.get('last_wars',7)); reasons=[]
        calendar=window(s['calendar'],config.get('attendance_window',{})); s['attendance']=round(sum(x['present'] for x in calendar)/len(calendar)*100,1) if calendar else None
        kills=sum(r['kills'] for r in recent); deaths=sum(r['deaths'] for r in recent)
        if recent and deaths and kills/deaths<config.get('kdr',0.5): reasons.append('KDR')
        if s['attendance'] is not None and s['attendance']<config.get('attendance',50): reasons.append('Attendance')
        participated={r['war'] for r in s['calendar'] if r['present']}
        checked=[e for e in rows(g,'event') if e.data.get('war') and any(x['member']==s['id'] and not x.get('waitlisted') for x in e.data.get('signups',[]))]
        checked_keys={item['id'] for item in window([{'id':e.key,**e.data} for e in checked],config.get('no_show_window',{}))}; checked=[e for e in checked if e.key in checked_keys]
        misses=sum(e.data['war'] not in participated for e in checked)
        if s['miss_streak']>=config.get('miss_streak',3) or (len(checked)>=config.get('min_events',3) and misses/max(len(checked),1)*100>=config.get('no_show',50)): reasons.append('No-show')
        for a in assignments:
            if a.data['member']!=s['id']: continue
            if a.data['status']=='active': reasons=[]
            elif a.data.get('resolved_at') and datetime.fromisoformat(a.data['resolved_at'])+timedelta(days=config.get('cooldown_days',7))>datetime.now(timezone.utc): reasons=[]
        if reasons: result.append({**s,'reasons':reasons})
    return result

def handle(g,action,p,role,user):
    require(role)
    if action=='notify':
        from .community import preview
        assignment=get(g,'assignment',p['assignment']);lead=get(g,'lead',assignment.data['lead']);member=get(g,'member',assignment.data['member'])
        return preview(g,'lead:'+assignment.key,f"{lead.data['name']}: mentor {member.data['name']}.",g.config.get('channels',{}).get('leads','preview'))
    if action=='settings':
        require(role,'owner')
        config={'enabled':bool(p.get('enabled',True))}
        for key,default,maximum in [('kdr',0.5,100),('attendance',50,100),('no_show',50,100),('grace_days',7,365),('cooldown_days',7,365),('miss_streak',3,1000),('last_wars',7,1000),('min_events',3,1000)]: config[key]=number(p.get(key,default),key,0,maximum) if key in ['kdr','attendance','no_show'] else integer(p.get(key,default),key,1 if key in ['last_wars','min_events'] else 0,maximum)
        for kind in ['kdr','attendance','no_show']:
            mode=choice(p.get(kind+'_mode','wars'),['all','wars','days','month'],'window mode'); size=integer(p.get(kind+'_size',7),'window size',1,1000); config[kind+'_window']={'mode':mode,'size':size}
        g.config['performance']=config; g.save(); return config
    if action=='lead':
        require(role,'owner'); return public(save(g,'lead',{'name':text(p['name']),'capacity':integer(p['capacity'],'capacity',1,100)},p.get('id')))
    if action=='assign':
        require(role,'owner'); get(g,'member',p['member']); lead=get(g,'lead',p['lead'])
        active=[r for r in rows(g,'assignment') if r.data['status']=='active']
        if any(r.data['member']==p['member'] for r in active): raise Invalid('Member already has an assignment')
        if sum(r.data['lead']==lead.key for r in active)>=lead.data['capacity']: raise Invalid('Lead is at capacity')
        return public(save(g,'assignment',{'member':p['member'],'lead':lead.key,'status':'active','at':now(),'notes':p.get('notes','')}))
    if action=='resolve':
        a=get(g,'assignment',p['assignment']); a.data.update(status='resolved',resolved_at=now(),outcome=text(p['outcome'],maximum=4000)); a.save(); return public(a)
    if action=='link_event':
        e=get(g,'event',p['event']); w=get(g,'war',p['war']); e.data['war']=w.key; e.save(); return public(e)
    raise Invalid('Unknown coaching action')
