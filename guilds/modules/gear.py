from .core import *

def handle(g,action,p,role,user):
    if action=='rival':
        require(role)
        return public(save(g,'rival',{'name':text(p['name']),'average_score':number(p['average_score'],'average gear score',0,3000),'members':integer(p['members'],'member count',1,1000),'at':now()},p.get('id')))
    owner_or_self(g,role,user,p['member'])
    if action=='save':
        ap=integer(p['ap'],'AP',0,1000); aap=integer(p['aap'],'AAP',0,1000); dp=integer(p['dp'],'DP',0,2000)
        # Independent prototype convention; documented and inspectable.
        return public(save(g,'gear',{'member':p['member'],'ap':ap,'aap':aap,'dp':dp,'score':max(ap,aap)+dp,'at':now(),'current':True}))
    if action=='delete':
        for r in rows(g,'gear'):
            if r.data['member']==p['member']: r.data['current']=False; r.save()
        return {'removed_current':True}
    raise Invalid('Unknown gear action')

def current(g):
    result={}
    for r in rows(g,'gear'):
        if r.data.get('current'): result[r.data['member']]=public(r)
    return sorted(result.values(),key=lambda r:r['score'],reverse=True)


def rankings(g):
    own=current(g)
    result=[{'name':g.name,'average_score':round(sum(r['score'] for r in own)/len(own),2) if own else 0,'members':len(own),'source':'local gear records'}]
    result.extend({**public(r),'source':'reviewed rival snapshot'} for r in rows(g,'rival'))
    return sorted(result,key=lambda r:r['average_score'],reverse=True)
