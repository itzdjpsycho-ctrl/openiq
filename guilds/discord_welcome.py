"""Welcome role buttons share a whitelist and require the intended member's access."""
import os
import httpx
from .modules.core import Invalid,owner_or_self,save
from .services import access,execute
from .discord_tickets import snowflake

def components(g,member):
    from .discord_components import signed_id
    roles=g.config.get('welcome',{}).get('role_ids',{})
    buttons=[{'type':2,'style':1,'label':str(label)[:80],'custom_id':signed_id('welcome',g,member.key,snowflake(role_id,'welcome role ID'))} for label,role_id in list(roles.items())[:25]]
    return [{'type':1,'components':buttons[i:i+5]} for i in range(0,len(buttons),5)]

def choose(user,g,member_key,role_id,enabled=False):
    member=owner_or_self(g,access(user,g),user,member_key)
    config=g.config.get('welcome',{});roles=config.get('role_ids',{})
    label=next((label for label,value in roles.items() if str(value)==str(role_id)),None)
    if label is None:
        raise Invalid('This welcome role is no longer available')
    if label not in config.get('roles',['Raider','Social']):
        raise Invalid('This role is not enabled for welcome selection')
    if enabled:
        if os.getenv('ENABLE_DISCORD_DELIVERY')!='1' or not os.getenv('DISCORD_BOT_TOKEN'):
            raise Invalid('Discord delivery is not enabled')
        server=snowflake(g.server_id,'server ID');target=snowflake(member.data.get('discord_id'),'member account link');role_id=snowflake(role_id,'welcome role ID')
        response=httpx.put(f'https://discord.com/api/v10/guilds/{server}/members/{target}/roles/{role_id}',headers={'Authorization':'Bot '+os.environ['DISCORD_BOT_TOKEN']},timeout=15)
        response.raise_for_status()
    result=execute(user,g.pk,'operations','welcome_role',{'member':member.key,'role':label})
    return {**result,'delivery':'Discord' if enabled else 'local'}
