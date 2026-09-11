from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from guilds.models import Guild
from guilds.discord_tickets import synchronize

class Command(BaseCommand):
    help='Preview a private ticket channel, or explicitly synchronize it with --send.'
    def add_arguments(self,parser):
        parser.add_argument('ticket');parser.add_argument('--guild',type=int,required=True);parser.add_argument('--user',default='demo');parser.add_argument('--send',action='store_true')
    def handle(self,*args,**options):
        result=synchronize(User.objects.get(username=options['user']),Guild.objects.get(pk=options['guild']),options['ticket'],enabled=options['send'])
        self.stdout.write(str(result))
