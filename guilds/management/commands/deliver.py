from django.core.management.base import BaseCommand,CommandError
from guilds.models import Outbox
from guilds.delivery import deliver
class Command(BaseCommand):
    help='Preview a notification, or explicitly send/update it with --send and delivery enabled.'
    def add_arguments(self,parser):parser.add_argument('id',type=int);parser.add_argument('--send',action='store_true')
    def handle(self,*args,**options):
        try:self.stdout.write(str(deliver(Outbox.objects.get(pk=options['id']),enabled=options['send'])))
        except Exception as exc:raise CommandError(str(exc))
