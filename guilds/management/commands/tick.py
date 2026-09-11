from django.core.management.base import BaseCommand
from guilds.models import Guild,Access
from guilds.services import execute
class Command(BaseCommand):
    help='Process scheduled work once. Notifications remain local previews.'
    def handle(self,*args,**options):
        for g in Guild.objects.all():
            owner=Access.objects.filter(guild=g,role='owner').select_related('user').first()
            if owner:self.stdout.write(str(execute(owner.user,g.pk,'operations','tick',{})))
