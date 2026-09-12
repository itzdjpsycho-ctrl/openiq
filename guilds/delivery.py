"""Explicitly enabled Discord delivery; default behavior is always a local preview."""
import os
import httpx
import hashlib
from .models import Outbox,Record
from .modules.core import save,Invalid

def deliver(item,enabled=False):
    if not enabled:return {'status':'preview','text':item.text,'channel':item.channel}
    if os.getenv('ENABLE_DISCORD_DELIVERY')!='1' or not os.getenv('DISCORD_BOT_TOKEN'):raise Invalid('Discord delivery is not enabled')
    if not item.channel.isdecimal():raise Invalid('Set a numeric Discord channel ID before delivery')
    previous=Record.objects.filter(guild=item.guild,kind='delivery',key=str(item.pk)).first()
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
            while True:
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
        else:
            save(item.guild,'delivery_pending',{'channel':item.channel},str(item.pk))
    payload['embeds']=[*payload.get('embeds',[]),{'footer':{'text':marker}}]
    if method=='POST':
        payload['nonce']=hashlib.sha256(marker.encode()).hexdigest()[:24]
        payload['enforce_nonce']=True
    response=httpx.request(method,url,headers={'Authorization':'Bot '+os.environ['DISCORD_BOT_TOKEN']},json=payload,timeout=15)
    response.raise_for_status();message=response.json()
    save(item.guild,'delivery',{'message_id':message['id'],'channel':item.channel},str(item.pk));item.status='sent';item.save()
    Record.objects.filter(guild=item.guild,kind='delivery_pending',key=str(item.pk)).delete()
    return {'status':'sent','message_id':message['id']}
