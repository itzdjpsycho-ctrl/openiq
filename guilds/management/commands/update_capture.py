from django.core.management.base import BaseCommand
from guilds.updater import inspect_release,install_release
class Command(BaseCommand):
    help='Check or install a trusted local capture release. No remote publication or connection.'
    def add_arguments(self,p):p.add_argument('manifest');p.add_argument('destination');p.add_argument('--install',action='store_true')
    def handle(self,*args,**o):self.stdout.write(str((install_release if o['install'] else inspect_release)(o['manifest'],o['destination'])))
