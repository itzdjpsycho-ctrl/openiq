from guilds.models import Guild, Record, Access
from .core import *
from .analytics import calculate

def visible(g):
    return [r for r in Record.objects.filter(kind='alliance') if str(g.pk) in r.data['guilds']]

def handle(g,action,p,role,user):
    require(role,'owner')
    if action=='create':
        ids=[str(g.pk)]+[str(x) for x in p.get('partners',[])]
        if len(ids)!=len(set(ids)) or not 2<=len(ids)<=4: raise Invalid('Choose 1–3 distinct partner guilds')
        if Guild.objects.filter(pk__in=ids).count()!=len(ids): raise Invalid('Unknown guild')
        if any(r.data['status'] in ['pending','active'] for r in visible(g)): raise Invalid('Guild already has an active or pending alliance')
        for r in Record.objects.filter(kind='alliance'):
            if r.data['status'] in ['pending','active'] and set(ids)&set(r.data['guilds']): raise Invalid('A partner already belongs to an alliance')
        return public(save(g,'alliance',{'name':text(p['name'],'alliance name',50),'guilds':{i:'accepted' if i==str(g.pk) else 'pending' for i in ids},'status':'pending'}))
    a=next((r for r in visible(g) if r.key==p['alliance']),None)
    if not a: raise Invalid('Alliance not found')
    if action=='respond':
        if a.data['status']!='pending' or a.data['guilds'][str(g.pk)]!='pending': raise Invalid('Invitation is no longer pending')
        response=choice(p['response'],['accepted','declined'],'response'); a.data['guilds'][str(g.pk)]=response
        if response=='declined':
            a.data['status']='disbanded'; a.data['guilds']={k:'cancelled' if v=='pending' else v for k,v in a.data['guilds'].items()}
        elif all(v=='accepted' for v in a.data['guilds'].values()): a.data['status']='active'
        a.save(); return public(a)
    if action=='leave':
        a.data['status']='disbanded'; a.save(); return public(a)
    raise Invalid('Unknown alliance action')

def overview(g):
    result=[]
    for a in visible(g):
        d=public(a); d['contributions']=[]; d['full_contributions']=[]; d['events']=[]; d['history']=[]; d['roster']=[]
        if d['status']=='active':
            for gid in d['guilds']:
                partner=Guild.objects.get(pk=gid)
                d['events'].extend({'guild':partner.name,'id':e.key,**e.data} for e in rows(partner,'event') if e.data.get('alliance_share'))
                d['history'].extend({'guild':partner.name,'id':w.key,**w.data} for w in rows(partner,'war') if w.data.get('alliance_included'))
                d['roster'].extend({'guild':partner.name,'name':m.data['name'],'class':m.data.get('class','Unknown')} for m in rows(partner,'member') if m.data.get('active'))
                d['full_contributions'].append({'guild':partner.name,**calculate(partner,alliance_only=True,exclude_exceptions=False)['totals']})
                d['contributions'].append({'guild':partner.name,**calculate(partner,alliance_only=True)['totals']})
        d['kills']=sum(x['kills'] for x in d['contributions']); d['deaths']=sum(x['deaths'] for x in d['contributions']); d['kdr']=kdr(d['kills'],d['deaths']); result.append(d)
    return result
