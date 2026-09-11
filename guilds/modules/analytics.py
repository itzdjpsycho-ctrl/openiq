from collections import defaultdict
from .core import *

def eligible(member, day):
    d=member.data
    return day>=d.get('joined','0000') and not any(v['start']<=day<=v['end'] for v in d.get('vacations',[]))

def calculate(g, filters=None, alliance_only=False, exclude_exceptions=True):
    f=filters or {}; members=rows(g,'member'); lookup={m.key:m for m in members}
    wars=sorted([w for w in rows(g,'war') if (not f.get('type') or w.data['type']==f['type']) and (not f.get('month') or w.data['date'].startswith(f['month'])) and (f.get('capped') in (None,'') or w.data['capped']==(str(f['capped']).lower()=='true')) and (not alliance_only or w.data.get('alliance_included'))],key=lambda w:w.data['date'])
    stats={m.key:{'id':m.key,'name':m.data['name'],'kills':0,'deaths':0,'present':0,'eligible':0,'timeline':[],'calendar':[]} for m in members}
    totals={'wars':len(wars),'kills':0,'deaths':0,'wins':0,'losses':0,'draws':0}; timeline=[]; classes=defaultdict(lambda:{'kills':0,'deaths':0,'participants':0})
    for w in wars:
        d=w.data; totals[{'Win':'wins','Loss':'losses','Draw':'draws'}[d['result']]]+=1; wk=wd=0
        ps={r['member']:r for r in d['participants']}
        for m in members:
            st=stats[m.key]; row=ps.get(m.key)
            if eligible(m,d['date']): st['calendar'].append({'date':d['date'],'present':bool(row),'war':w.key})
            if row and not d.get('excluded') and not row.get('excluded'):
                st['kills']+=row['kills']; st['deaths']+=row['deaths']; st['timeline'].append({'date':d['date'],'kills':row['kills'],'deaths':row['deaths'],'kdr':kdr(row['kills'],row['deaths'])})
                if not exclude_exceptions or not m.data.get('exception'):
                    wk+=row['kills']; wd+=row['deaths']; cl=classes[row.get('class','Unknown')]; cl['kills']+=row['kills']; cl['deaths']+=row['deaths']; cl['participants']+=1
        totals['kills']+=wk; totals['deaths']+=wd; timeline.append({'date':d['date'],'kills':wk,'deaths':wd,'kdr':kdr(wk,wd),'war':w.key})
    for m in members:
        st=stats[m.key]; recent=st['calendar'][-7:]; st['eligible']=len(recent); st['present']=sum(r['present'] for r in recent); st['attendance']=round(100*st['present']/len(recent),1) if recent else None; st['kdr']=kdr(st['kills'],st['deaths'])
        st['miss_streak']=0
        for r in reversed(st['calendar']):
            if r['present']: break
            st['miss_streak']+=1
        t=st['timeline']; st['improvement']=(t[-1]['kills']/max(t[-1]['deaths'],1)-t[0]['kills']/max(t[0]['deaths'],1)) if len(t)>1 else 0
    totals['kdr']=kdr(totals['kills'],totals['deaths']); decided=totals['wins']+totals['losses']; totals['win_rate']=round(100*totals['wins']/decided,1) if decided else 0
    awards={}
    candidates=[s for s in stats.values() if s['timeline']]
    if candidates:
        awards={'MVP':max(candidates,key=lambda s:s['kills'])['name'],'Most improved':max(candidates,key=lambda s:s['improvement'])['name'],'Most deaths':max(candidates,key=lambda s:s['deaths'])['name'],'Attendance':max(candidates,key=lambda s:s['attendance'] or 0)['name']}
    composition=defaultdict(int)
    for m in members:
        if m.data.get('active'): composition[m.data.get('class','Unknown')]+=1
    return {'totals':totals,'members':list(stats.values()),'timeline':timeline,'classes':dict(classes),'composition':dict(composition),'awards':awards}
