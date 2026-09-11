import json
from django.core.management.base import BaseCommand,CommandError
from django.contrib.auth.models import User
from guilds.services import execute
class Command(BaseCommand):
    help='Run a Discord-compatible command locally without connecting to Discord.'
    def add_arguments(self,parser):
        parser.add_argument('command');parser.add_argument('--guild',type=int,default=1);parser.add_argument('--user',default='demo');parser.add_argument('--arguments',default='{}')
    def handle(self,*args,**options):
        result=execute(User.objects.get(username=options['user']),options['guild'],'commands','run',{'command':options['command'],'arguments':json.loads(options['arguments'])})
        self.stdout.write(json.dumps(result,indent=2))
