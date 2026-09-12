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
    if module not in MODULES: raise Invalid('Unknown module')
    if not isinstance(payload,dict): raise Invalid('Payload must be an object')
    result=MODULES[module].handle(g,action,payload,role,user)
    if module in ['events','commands'] and isinstance(result,dict) and result.get('id'):
        from guilds.models import Outbox,Record
        event=Record.objects.filter(guild=g,kind='event',key=str(result['id'])).first()
        if event and Outbox.objects.filter(guild=g,key=f'{g.pk}:event:{event.key}').exists():
            MODULES['community'].handle(g,'post_event',{'event':event.key},'admin',user)
    if g.pk: Audit.objects.create(guild=g,actor=user.username,action=module+'.'+action,data={'result_id':result.get('id')} if isinstance(result,dict) else {})
    return result
