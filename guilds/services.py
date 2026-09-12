from django.db import transaction
from django.db.models import F
from guilds.models import Guild, Access, Audit
from .modules.core import Invalid
from .modules.registry import MODULES
from django.core.exceptions import PermissionDenied

def access(user,guild):
    if not user.is_authenticated: raise PermissionDenied('Sign in first')
    try: return Access.objects.get(user=user,guild=guild).role
    except Access.DoesNotExist: raise PermissionDenied('You do not have access to this guild')

@transaction.atomic
def execute(user,guild_id,module,action,payload):
    # ORM UPDATE serializes mutations: SQLite takes its writer lock; PostgreSQL
    # locks the guild row until this transaction ends. Read records afterward.
    role=access(user,guild_id)
    Guild.objects.filter(pk=guild_id).update(revision=F('revision')+1)
    g=Guild.objects.get(pk=guild_id)
    from guilds.models import Record
    before_wars={r.key:r.data for r in Record.objects.filter(guild=g,kind='war')} if module in ('wars','live','coaching','commands','roster','admin') else None
    if module not in MODULES: raise Invalid('Unknown module')
    if not isinstance(payload,dict): raise Invalid('Payload must be an object')
    from .catalog import ACTIONS
    from .modules.core import require
    declared=next((item for item in ACTIONS if item['module']==module and item['action']==action),None)
    if declared:require(role,declared['role'])
    result=MODULES[module].handle(g,action,payload,role,user)
    if before_wars is not None and g.pk:
        from .modules.core import save,now
        after_wars={r.key:r.data for r in Record.objects.filter(guild=g,kind='war')}
        for key in before_wars.keys()|after_wars.keys():
            before=before_wars.get(key);after=after_wars.get(key)
            if before!=after:save(g,'war_revision',{'war':key,'actor':user.username,'action':module+'.'+action,'at':now(),'before':before,'after':after})
    if module in ['events','commands'] and isinstance(result,dict) and result.get('id'):
        from guilds.models import Outbox,Record
        event=Record.objects.filter(guild=g,kind='event',key=str(result['id'])).first()
        if event and Outbox.objects.filter(guild=g,key=f'{g.pk}:event:{event.key}').exists():
            MODULES['community'].handle(g,'post_event',{'event':event.key},'admin',user)
    if g.pk: Audit.objects.create(guild=g,actor='privacy-request' if module=='privacy' and action in ('anonymize','delete') else user.username,action=module+'.'+action,data={'result_id':result.get('id')} if isinstance(result,dict) else {})
    return result
