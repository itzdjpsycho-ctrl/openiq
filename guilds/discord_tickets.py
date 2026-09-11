"""Optional private Discord ticket-channel adapter; previews never use the network."""
import os
import httpx
from .models import Record,Outbox
from .modules.core import Invalid,get,require,rows,save
from .services import access
from .delivery import deliver

VIEW=1<<10
SEND=1<<11
HISTORY=1<<16

def snowflake(value,label):
    value=str(value or '')
    if not value.isdecimal():
        raise Invalid('Configure a numeric Discord '+label)
    return value

def plan(g,ticket):
    config=g.config.get('tickets',{})
    server=snowflake(g.server_id,'server ID')
    bot=snowflake(config.get('bot_user_id'),'bot user ID in ticket settings')
    member=next((m for m in rows(g,'member') if str(m.data.get('user_id'))==str(ticket.data['user'])),None)
    requester=snowflake(member.data.get('discord_id') if member else None,'account link for the ticket author')
    category=next((c for c in rows(g,'ticket_category') if c.data['name']==ticket.data['category']),None)
    staff=snowflake(category.data.get('staff_role') if category else config.get('staff_role'),'ticket staff role')
    if staff==server:
        raise Invalid('The ticket staff role cannot be @everyone')
    closed=ticket.data['status']=='closed'
    grants=VIEW|SEND|HISTORY
    payload={'name':('closed-' if closed else 'ticket-')+ticket.key[:8],'type':0,'topic':ticket.data['subject'][:1024],
             'permission_overwrites':[{'id':server,'type':0,'deny':str(VIEW),'allow':'0'},
                {'id':requester,'type':1,'allow':str(VIEW|HISTORY if closed else grants),'deny':str(SEND if closed else 0)},
                {'id':staff,'type':0,'allow':str(grants),'deny':'0'},
                {'id':bot,'type':1,'allow':str(grants),'deny':'0'}]}
    if config.get('category_id'):
        payload['parent_id']=snowflake(config['category_id'],'ticket category ID')
    return {'server':server,'channel':payload,'status':ticket.data['status']}

def synchronize(user,g,ticket_key,enabled=False):
    require(access(user,g))
    ticket=get(g,'ticket',ticket_key);planned=plan(g,ticket)
    if not enabled:
        return {'mode':'preview',**planned}
    if os.getenv('ENABLE_DISCORD_DELIVERY')!='1' or not os.getenv('DISCORD_BOT_TOKEN'):
        raise Invalid('Discord delivery is not enabled')
    previous=Record.objects.filter(guild=g,kind='ticket_channel',key=ticket.key).first()
    endpoint='/channels/'+previous.data['channel_id'] if previous else '/guilds/'+planned['server']+'/channels'
    response=httpx.request('PATCH' if previous else 'POST','https://discord.com/api/v10'+endpoint,
                          headers={'Authorization':'Bot '+os.environ['DISCORD_BOT_TOKEN']},json=planned['channel'],timeout=15)
    response.raise_for_status();channel_id=snowflake(response.json()['id'],'channel ID')
    save(g,'ticket_channel',{'channel_id':channel_id,'status':ticket.data['status']},ticket.key)
    transcript=ticket.data['subject']+'\n'+ticket.data['text']+'\n'+'\n'.join(r['by']+': '+r['text'] for r in ticket.data['replies'])
    for offset in range(0,len(transcript),1900):
        item,_=Outbox.objects.update_or_create(guild=g,key=f'{g.pk}:ticket:{ticket.key}:{offset//1900}',defaults={'channel':channel_id,'text':transcript[offset:offset+1900],'status':'preview'})
        deliver(item,enabled=True)
    return {'mode':'sent','channel_id':channel_id,'status':ticket.data['status']}
