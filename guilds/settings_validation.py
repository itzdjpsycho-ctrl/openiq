"""Validate nested settings at the shared service boundary."""
from .modules.core import Invalid


def validate(config,server=''):
    for key in ('channels','roles','tickets','welcome','command_permissions','capture','integrations','retention','weekly','sync','recruitment'):
        if key in config and not isinstance(config[key],dict):raise Invalid(key+' settings must be an object')
    def snowflake(value,optional=False):
        if optional and value in ('','preview',None):return
        if not isinstance(value,(str,int)) or isinstance(value,bool) or not str(value).isdecimal():raise Invalid('Discord IDs must contain only digits')
    for value in config.get('channels',{}).values():snowflake(value,True)
    for key,value in config.get('tickets',{}).items():
        if key in ('bot_user_id','staff_role','category_id'):snowflake(value,True)
    for tier,ids in config.get('roles',{}).items():
        if tier not in ('owner','admin','member'):raise Invalid('Unknown access tier')
        ids=[ids] if isinstance(ids,str) else ids
        if not isinstance(ids,list):raise Invalid('Access role IDs must be a list')
        for role in ids:
            snowflake(role)
            if tier in ('owner','admin') and str(role)==server:raise Invalid('Everyone cannot be an officer role')
    welcome=config.get('welcome',{})
    if 'role_ids' in welcome:
        if not isinstance(welcome['role_ids'],dict) or len(welcome['role_ids'])>25:raise Invalid('Configure at most 25 welcome roles')
        for label,role in welcome['role_ids'].items():
            if not label.strip() or len(label)>80:raise Invalid('Welcome role labels must contain 1–80 characters')
            snowflake(role)
    from .modules.commands import COMMANDS
    for command,tier in config.get('command_permissions',{}).items():
        if command not in COMMANDS or tier not in ('owner','admin','member'):raise Invalid('Invalid command permission override')
    for key,value in config.get('capture',{}).items():
        if key=='enabled':
            if not isinstance(value,bool):raise Invalid('Capture enabled must be a boolean')
        elif key in ('token_hours','diagnostic_entries'):
            maximum=72 if key=='token_hours' else 200
            if isinstance(value,bool) or not isinstance(value,int) or not 1<=value<=maximum:raise Invalid(key+' is outside its supported range')
        else:raise Invalid('Unknown capture setting')
    for key,value in config.get('integrations',{}).items():
        if key not in ('twitch','ollama') or not isinstance(value,bool):raise Invalid('Integration toggles must be booleans')
    if 'replace_selection' in welcome and not isinstance(welcome['replace_selection'],bool):raise Invalid('Welcome replacement must be a boolean')
    from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
    for kind in ('weekly','sync'):
        schedule=config.get(kind,{})
        if 'enabled' in schedule and not isinstance(schedule['enabled'],bool):raise Invalid('Schedule enabled must be a boolean')
        for key,maximum in (('weekday',6),('hour',23)):
            if key in schedule and (isinstance(schedule[key],bool) or not isinstance(schedule[key],int) or not 0<=schedule[key]<=maximum):raise Invalid('Invalid schedule '+key)
        if 'timezone' in schedule:
            try:ZoneInfo(schedule['timezone'])
            except (ZoneInfoNotFoundError,ValueError,TypeError):raise Invalid('Invalid schedule timezone')
        if 'channel' in schedule:snowflake(schedule['channel'],True)
