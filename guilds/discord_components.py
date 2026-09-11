"""Discord component payloads and authorization share the local event services."""
from .modules.core import Invalid,own_member
from .models import Guild,Record
from .services import execute,access

def event_components(g,event):
    # Discord allows at most 5 action rows with at most 5 buttons each.
    buttons=[{'type':2,'style':1,'label':team['name'][:80],'custom_id':f'signup:{g.pk}:{event.key}:{i}'} for i,team in enumerate(event.data['teams'][:24])]
    buttons.append({'type':2,'style':2,'label':'Withdraw','custom_id':f'signup:{g.pk}:{event.key}:withdraw'})
    return [{'type':1,'components':buttons[i:i+5]} for i in range(0,len(buttons),5)]

def process(user,custom_id,deliver_roles=False):
    fields=custom_id.split(':')
    if len(fields)!=4 or fields[0] not in ['signup','welcome']:raise Invalid('Unknown component')
    kind,gid,key,index=fields;g=Guild.objects.get(pk=gid);access(user,g)
    if kind=='welcome':
        from .discord_welcome import choose
        return choose(user,g,key,index,enabled=deliver_roles)
    member=own_member(g,user)
    if not member:raise Invalid('Ask an officer to link your account first')
    event=Record.objects.get(guild=g,kind='event',key=key)
    try:
        if index!='withdraw' and (not index.isdecimal() or int(index)>=len(event.data['teams'])):raise ValueError()
        team='' if index=='withdraw' else event.data['teams'][int(index)]['name']
    except (ValueError,IndexError):raise Invalid('Team no longer exists')
    return execute(user,g.pk,'events','signup',{'event':key,'member':member.key,'team':team})
