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
    # A database write acquires SQLite's writer lock before reading mutable records.
    role=access(user,guild_id)
    Guild.objects.filter(pk=guild_id).update(revision=F('revision')+1)
    g=Guild.objects.get(pk=guild_id)
    if module not in MODULES: raise Invalid('Unknown module')
    if not isinstance(payload,dict): raise Invalid('Payload must be an object')
    result=MODULES[module].handle(g,action,payload,role,user)
    Audit.objects.create(guild=g,actor=user.username,action=module+'.'+action,data={'result_id':result.get('id')} if isinstance(result,dict) else {})
    return result
