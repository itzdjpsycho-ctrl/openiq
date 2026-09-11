import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from .models import Guild,Record,Access,Audit,Outbox
from .services import access,execute
from .modules.core import public,Invalid
from .modules import analytics,alliances,coaching,gear,live,integrations,intelligence
from .catalog import ACTIONS

@login_required
def index(request):
    guilds=Guild.objects.filter(access__user=request.user).order_by('name')
    return render(request,'dashboard.html',{'guilds':guilds,'actions':ACTIONS})

@login_required
def state(request,guild_id):
    g=get_object_or_404(Guild,pk=guild_id); role=access(request.user,g)
    records={}
    private={'lead','assignment','adoption','application','import'}
    for r in Record.objects.filter(guild=g).exclude(kind='alliance'):
        if role=='member' and r.kind in private: continue
        if r.kind in ['ticket','reminder','minigame'] and role=='member' and r.data.get('user',r.key)!=request.user.pk and str(r.data.get('user',r.key))!=str(request.user.pk): continue
        d=public(r)
        if r.kind=='member' and role=='member': d.pop('notes',None)
        if r.kind=='session': d['summary']=live.summarize(r)
        records.setdefault(r.kind,[]).append(d)
    records['alliance']=alliances.overview(g)
    result={'guild':{'id':g.pk,'name':g.name,'revision':g.revision,'config':g.config if role=='owner' else {}},'role':role,'user':{'id':request.user.pk,'name':request.user.username},'records':records,'analytics':analytics.calculate(g,request.GET),'intelligence':intelligence.extended(g),'rankings':gear.rankings(g),'gear':gear.current(g),'flags':coaching.flags(g) if role!='member' else [],'actions':[a for a in ACTIONS if {'member':0,'admin':1,'owner':2}[a['role']]<={'member':0,'admin':1,'owner':2}[role]],'guilds':list(Guild.objects.values('id','name')),'accounts':list(Access.objects.filter(guild=g).values('user_id','user__username','role')) if role=='owner' else []}
    if role!='member': result.update(outbox=list(Outbox.objects.filter(guild=g).order_by('-created').values('id','text','status','created')[:100]),audit=list(Audit.objects.filter(guild=g).order_by('-created').values('actor','action','created')[:100]))
    return JsonResponse(result)

@login_required
@require_POST
def action(request,guild_id,module,name):
    try:
        payload=json.loads(request.body)
        return JsonResponse({'ok':True,'result':execute(request.user,guild_id,module,name,payload)})
    except (Invalid,KeyError,TypeError,json.JSONDecodeError) as e: return JsonResponse({'ok':False,'error':str(e)},status=400)
    except PermissionDenied as e: return JsonResponse({'ok':False,'error':str(e)},status=403)

@login_required
@require_POST
def ocr_view(request,guild_id):
    role=access(request.user,guild_id)
    if role=='member' and request.POST.get('mode')!='gear': raise PermissionDenied()
    try:
        files=request.FILES.getlist('images')
        if not files or len(files)>10: raise Invalid('Choose 1–10 images')
        texts=[integrations.ocr(f.read()) for f in files]
        result={'texts':texts,'review_required':True}
        if request.POST.get('mode')=='gear':result['gear']=integrations.gear_numbers(texts)
        else:
            try:result['draft']=execute(request.user,guild_id,'wars','review',{'rows':integrations.paired_scores(texts)})
            except Invalid as exc:result['review_error']=str(exc)
        return JsonResponse(result)
    except (Invalid,ValueError) as e: return JsonResponse({'error':str(e)},status=400)

def recap(request,token):
    session=next((r for r in Record.objects.filter(kind='session') if r.data.get('public') and r.data.get('share_token')==str(token)),None)
    if not session:
        from django.http import Http404
        raise Http404()
    return render(request,'recap.html',{'session':session.data,'summary':live.summarize(session)})

@login_required
@require_POST
def onboard(request):
    from django.db import transaction
    from .modules.core import text
    try:
        p=json.loads(request.body)
        with transaction.atomic():
            name=text(p['name'],'guild name',80)
            if Guild.objects.filter(name__iexact=name).exists():raise Invalid('That guild already exists')
            g=Guild.objects.create(name=name,region=text(p.get('region','NA'),'region',12),server_id=str(p.get('server_id','')))
            Access.objects.create(guild=g,user=request.user,role='owner')
            if p.get('names'):execute(request.user,g.pk,'roster','sync',{'names':p['names']})
        return JsonResponse({'id':g.pk,'name':g.name})
    except (Invalid,KeyError,TypeError,ValueError) as e:return JsonResponse({'error':str(e)},status=400)

@login_required
def ally_event(request,token):
    from .modules.alliances import visible
    from django.http import Http404
    e=next((r for r in Record.objects.filter(kind='event') if r.data.get('alliance_share') and r.data.get('share_token')==str(token)),None)
    if not e:raise Http404()
    accessible=set(Guild.objects.filter(access__user=request.user).values_list('id',flat=True))
    if e.guild_id not in accessible and not any(a.data['status']=='active' and accessible.intersection(map(int,a.data['guilds'])) for a in visible(e.guild)):raise PermissionDenied()
    from .modules.core import rows
    names={m.key:m.data['name'] for m in rows(e.guild,'member')}
    return render(request,'ally_event.html',{'event':e.data,'guild':e.guild.name,'signups':[{**s,'name':names.get(s['member'],'Unknown')} for s in e.data['signups']]})
