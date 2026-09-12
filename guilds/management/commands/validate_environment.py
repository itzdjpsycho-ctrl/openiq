"""Fail early on missing/unsafe deployment settings without echoing their values."""
import os
from urllib.parse import urlparse
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError


def problems(env,debug,service='web'):
    errors=[]
    for key in ('DEBUG','HTTPS','TRUST_PROXY','ALLOW_LOCAL_LOGIN','SEED_DEMO','ENABLE_BACKEND_ADMIN','ENABLE_DISCORD_DELIVERY','DISCORD_SYNC_GLOBAL'):
        if key in env and env[key] not in ('0','1'):errors.append(key+' must be 0 or 1')
    if env.get('ENABLE_DISCORD_DELIVERY')=='1' and not env.get('DISCORD_BOT_TOKEN'):errors.append('Enabled Discord delivery requires DISCORD_BOT_TOKEN')
    if not debug:
        if env.get('ALLOW_LOCAL_LOGIN')=='1':errors.append('Production member password login must be disabled')
        if env.get('SEED_DEMO')=='1':errors.append('Production demo seeding must be disabled')
        if service=='web':
            for key in ('DISCORD_CLIENT_ID','DISCORD_CLIENT_SECRET','DISCORD_REDIRECT_URI'):
                if not env.get(key):errors.append('Production requires '+key)
            redirect=urlparse(env.get('DISCORD_REDIRECT_URI',''))
            if redirect.scheme!='https' or not redirect.hostname or redirect.username or redirect.query or redirect.fragment:
                errors.append('Production DISCORD_REDIRECT_URI must be an HTTPS callback URL')
    if env.get('DISCORD_CLIENT_ID') and not env['DISCORD_CLIENT_ID'].isdecimal():errors.append('DISCORD_CLIENT_ID must be numeric')
    if env.get('DISCORD_SYNC_GUILD') and not env['DISCORD_SYNC_GUILD'].isdecimal():errors.append('DISCORD_SYNC_GUILD must be numeric')
    if env.get('DISCORD_SYNC_GUILD') and env.get('DISCORD_SYNC_GLOBAL')=='1':errors.append('Choose one Discord command sync scope')
    return errors


class Command(BaseCommand):
    help='Validate the deployment environment before starting services; never print credentials.'
    def handle(self,*args,**options):
        errors=problems(os.environ,settings.DEBUG,os.getenv('OPENIQ_SERVICE','web'))
        if errors:raise CommandError('\n'.join(errors))
        self.stdout.write('Deployment environment is valid.')
