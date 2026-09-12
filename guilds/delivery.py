"""Explicitly enabled Discord delivery; default behavior is always a local preview."""
import os
import httpx
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
    response=httpx.request(method,url,headers={'Authorization':'Bot '+os.environ['DISCORD_BOT_TOKEN']},json=payload,timeout=15)
    response.raise_for_status();message=response.json()
    save(item.guild,'delivery',{'message_id':message['id'],'channel':item.channel},str(item.pk));item.status='sent';item.save()
    return {'status':'sent','message_id':message['id']}
