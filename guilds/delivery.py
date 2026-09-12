"""Explicitly enabled Discord delivery; default behavior is always a local preview."""
import os
import httpx
import hashlib
import time
import uuid
from django.db import transaction
from django.db.models import F
from .models import Guild
from .models import Outbox,Record
from .modules.core import save,Invalid

def deliver(item,enabled=False,queued=False):
    if not enabled:return _deliver(item,False)
    # Persist a claim before network I/O so concurrent commands/workers cannot
    # both create a message. A crashed process relinquishes its claim in an hour.
    claim=uuid.uuid4().hex
    with transaction.atomic():
        Guild.objects.filter(pk=item.guild_id).update(revision=F('revision')+1)
        state=Record.objects.filter(guild=item.guild,kind='delivery_retry',key=str(item.pk)).first()
        data=state.data if state else {}
        if data.get('lease_until',0)>time.time():return {'status':'busy'}
        item.refresh_from_db()
        if queued and item.status!='preview':return {'status':item.status}
        data.update(claim=claim,lease_until=time.time()+3600)
        save(item.guild,'delivery_retry',data,str(item.pk))
    try:
        result=_deliver(item,True)
    except Exception as exc:
        data.update(attempts=data.get('attempts',0)+1,lease_until=0)
        delay=min(3600,30*2**min(data['attempts']-1,7))
        if isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code==429:
            try:delay=max(delay,min(86400,float(exc.response.headers.get('Retry-After',delay))))
            except ValueError:pass
        data.update(next_attempt=time.time()+delay,error='Delivery failed; check configuration, permissions and remote outcome.')
        save(item.guild,'delivery_retry',data,str(item.pk))
        raise
    else:
        save(item.guild,'delivery_retry',{'attempts':0,'next_attempt':0,'lease_until':0},str(item.pk))
        return result


def _deliver(item,enabled=False):
    if not enabled:return {'status':'preview','text':item.text,'channel':item.channel}
    if os.getenv('ENABLE_DISCORD_DELIVERY')!='1' or not os.getenv('DISCORD_BOT_TOKEN'):raise Invalid('Discord delivery is not enabled')
    if not item.channel.isdecimal():raise Invalid('Set a numeric Discord channel ID before delivery')
    previous=Record.objects.filter(guild=item.guild,kind='delivery',key=str(item.pk)).first()
    if previous and previous.data['channel']!=item.channel:
        previous.delete();previous=None
        Record.objects.filter(guild=item.guild,kind='delivery_pending',key=str(item.pk)).delete()
    url=f'https://discord.com/api/v10/channels/{item.channel}/messages'
    if previous:url+='/'+previous.data['message_id']
    method='PATCH' if previous else 'POST'
    payload={'content':item.text[:2000],'allowed_mentions':{'parse':[]}}
    components=Record.objects.filter(guild=item.guild,kind='message_components',key=str(item.pk)).first()
    if components:
        payload['components']=components.data['components']
        payload['embeds']=components.data.get('embeds',[])
    marker='OpenIQ delivery '+str(item.guild_id)+':'+str(item.pk)
    if not previous:
        pending=Record.objects.filter(guild=item.guild,kind='delivery_pending',key=str(item.pk)).first()
        if pending:
            # Recover remote success after a lost response or failed local save.
            before=None
            for page in range(100):
                params={'limit':100}
                if before:params['before']=before
                found=httpx.request('GET',url,headers={'Authorization':'Bot '+os.environ['DISCORD_BOT_TOKEN']},params=params,timeout=15)
                found.raise_for_status();messages=found.json()
                match=next((m for m in messages if any(e.get('footer',{}).get('text')==marker for e in m.get('embeds',[])) and m.get('author',{}).get('bot')),None)
                if match:
                    previous=save(item.guild,'delivery',{'message_id':match['id'],'channel':item.channel},str(item.pk))
                    url+='/'+match['id'];method='PATCH';break
                if len(messages)<100:
                    raise Invalid('Delivery outcome is unresolved; inspect the channel before retrying. No duplicate message was sent.')
                before=messages[-1]['id']
            else:raise Invalid('Delivery history exceeds the reconciliation limit; inspect the channel before retrying.')
        else:
            save(item.guild,'delivery_pending',{'channel':item.channel},str(item.pk))
    payload['embeds']=[*payload.get('embeds',[]),{'footer':{'text':marker}}]
    if method=='POST':
        payload['nonce']=hashlib.sha256(marker.encode()).hexdigest()[:24]
        payload['enforce_nonce']=True
    response=httpx.request(method,url,headers={'Authorization':'Bot '+os.environ['DISCORD_BOT_TOKEN']},json=payload,timeout=15)
    if isinstance(response.status_code,int) and 400<=response.status_code<500 and response.status_code not in (408,):
        # A definite rejection did not create a message. A timeout or server
        # failure remains uncertain and must be reconciled before any POST.
        Record.objects.filter(guild=item.guild,kind='delivery_pending',key=str(item.pk)).delete()
    response.raise_for_status();message=response.json()
    save(item.guild,'delivery',{'message_id':message['id'],'channel':item.channel},str(item.pk))
    with transaction.atomic():
        Guild.objects.filter(pk=item.guild_id).update(revision=F('revision')+1)
        current_components=Record.objects.filter(guild=item.guild,kind='message_components',key=str(item.pk)).first()
        if (current_components.data if current_components else None)==(components.data if components else None):
            Outbox.objects.filter(pk=item.pk,text=item.text,channel=item.channel).update(status='sent')
    Record.objects.filter(guild=item.guild,kind='delivery_pending',key=str(item.pk)).delete()
    return {'status':'sent','message_id':message['id']}
