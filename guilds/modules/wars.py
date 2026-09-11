import csv, io
from difflib import SequenceMatcher
from .core import *

def participants(g, raw):
    if not isinstance(raw,list) or not raw: raise Invalid('At least one participant is required')
    seen=set(); result=[]
    for r in raw:
        m=get(g,'member',r['member'])
        if m.key in seen: raise Invalid('Duplicate member in war')
        seen.add(m.key)
        result.append({'member':m.key,'kills':integer(r['kills'],'kills'),'deaths':integer(r['deaths'],'deaths'),'class':r.get('class',m.data.get('class','Unknown')),'spec':r.get('spec',m.data.get('spec','Succession')),'excluded':bool(r.get('excluded',False))})
    return result

def handle(g,action,p,role,user):
    require(role)
    if action=='review':
        raw=p.get('rows')
        if raw is None:
            try: raw=list(csv.DictReader(io.StringIO(p['csv'])))
            except (TypeError,KeyError): raise Invalid('Supply CSV with name,kills,deaths columns')
        if not raw or len(raw)>1000: raise Invalid('Supply 1–1000 score rows')
        roster=rows(g,'member'); output=[]
        for r in raw:
            name=text(r.get('name',''),'name',80)
            scores=sorted([(SequenceMatcher(None,name.casefold(),m.data['name'].casefold()).ratio(),m) for m in roster],key=lambda x:x[0],reverse=True)
            score,match=scores[0] if scores else (0,None)
            output.append({'name':name,'member':match.key if match and score==1 else '', 'suggestion':match.key if match and score>=0.65 else '', 'confidence':round(score,3),'kills':integer(r.get('kills'),'kills'),'deaths':integer(r.get('deaths'),'deaths')})
        return public(save(g,'import',{'rows':output,'status':'review','created_by':user.pk}))
    if action=='finalize':
        draft=get(g,'import',p['import'])
        if draft.data['status']!='review': raise Invalid('This import was already finalized')
        data={**p,'participants':p.get('participants',draft.data['rows'])}
        result=handle(g,'save',data,role,user)
        draft.data.update(status='finalized',war=result['id']); draft.save(); return result
    if action=='save':
        key=p.get('id'); old=get(g,'war',key).data if key else {}
        data={**old,**{k:v for k,v in p.items() if k in ['note','excluded','alliance_included','session']}}
        data.update(date=date(p.get('date',old.get('date',now()[:10]))),type=choice(p.get('type',old.get('type','Node')),['Node','Siege'],'war type'),result=choice(p.get('result',old.get('result','Draw')),['Win','Loss','Draw'],'result'),capped=bool(p.get('capped',old.get('capped',False))),participants=participants(g,p.get('participants',old.get('participants'))))
        return public(save(g,'war',data,key))
    if action=='delete':
        get(g,'war',p['war']).delete(); return {'deleted':p['war']}
    raise Invalid('Unknown war action')
