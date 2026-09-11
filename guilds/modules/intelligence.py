"""Derived analytics and reusable character intelligence, independent of transport."""
from collections import defaultdict
from statistics import pstdev
from .core import *
from .analytics import calculate
from .live import summarize

def extended(g):
    a=calculate(g);ranked=[s for s in a['members'] if s['timeline']];awards=dict(a['awards'])
    if ranked:
        awards['Consistency']=min(ranked,key=lambda s:pstdev([r['kills']/max(r['deaths'],1) for r in s['timeline']]))['name']
        awards['Best war K/D']=max(ranked,key=lambda s:max(r['kills']/max(r['deaths'],1) for r in s['timeline']))['name']
        awards['Single-war kills']=max(ranked,key=lambda s:max(r['kills'] for r in s['timeline']))['name']
    profiles=defaultdict(lambda:{'kills':0,'deaths':0,'sessions':0,'classes':defaultdict(int),'players':defaultdict(lambda:{'kills':0,'deaths':0})})
    for session in rows(g,'session'):
        for enemy,s in summarize(session)['enemies'].items():
            p=profiles[enemy];p['kills']+=s['kills'];p['deaths']+=s['deaths'];p['sessions']+=1
            for cl,count in s['classes'].items():p['classes'][cl]+=count
            for name,stats in s['players'].items():
                for metric in ['kills','deaths']:p['players'][name][metric]+=stats[metric]
    matchups={}
    for member in rows(g,'member'):
        targets=defaultdict(lambda:{'kills':0,'deaths':0});names={member.data['name'],member.data.get('character','')}
        for session in rows(g,'session'):
            for e in session.data['events']:
                if e['kind']=='kill' and e['player'] in names:targets[e['target']]['kills']+=1
                if e['kind']=='death' and e['target'] in names:targets[e['player']]['deaths']+=1
        matchups[member.key]=dict(targets)
    return {'awards':awards,'enemy_profiles':dict(profiles),'matchups':matchups}

def handle(g,action,p,role,user):
    require(role)
    if action=='character':
        char=text(p['character'],'character',80);data={'character':char,'family':text(p['family'],'family',80),'class':text(p['class'],'class',40),'guild':text(p['guild'],'guild',80),'at':now()}
        r=save(g,'character',data,char.casefold())
        for s in rows(g,'session'):
            for e in s.data['events']:
                enemy=e['target'] if e['kind']=='kill' else e['player']
                if enemy.casefold()==char.casefold():e.update({'class':data['class'],'family':data['family']})
            s.save()
        return public(r)
    if action=='queue_lookup':
        character=text(p['character'],'character',80)
        return public(save(g,'lookup',{'character':character,'status':'pending','attempts':0},character.casefold()))
    if action=='resolve_queue':
        paused=Record.objects.filter(guild=g,kind='lookup_status',key='current').first()
        if paused and paused.data['paused_until']>now(): return {'paused_until':paused.data['paused_until'],'resolved':0}
        resolved=0
        for item in rows(g,'lookup'):
            if item.data['status']!='pending':continue
            found=Record.objects.filter(guild=g,kind='character',key=item.key).first()
            item.data['attempts']+=1
            if found:item.data.update(status='resolved',result=found.data);resolved+=1
            else:item.data['status']='needs_identification'
            item.save()
        return {'resolved':resolved}
    if action=='lookup_backoff':return public(save(g,'lookup_status',{'paused_until':timestamp(p['until']),'reason':'Remote rate limit'},'current'))
    raise Invalid('Unknown intelligence action')
