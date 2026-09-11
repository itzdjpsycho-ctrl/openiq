import time
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from guilds.capture import JsonLineTail
from guilds.services import execute
class Command(BaseCommand):
    help='Tail a normalized local JSONL event file into a session; no game packet decoding.'
    def add_arguments(self,parser):
        parser.add_argument('file');parser.add_argument('--session',required=True);parser.add_argument('--guild',type=int,default=1);parser.add_argument('--user',default='demo');parser.add_argument('--once',action='store_true')
    def handle(self,*args,**o):
        tail=JsonLineTail(o['file']);user=User.objects.get(username=o['user'])
        try:
            while True:
                events=tail.read()
                if events:self.stdout.write(str(execute(user,o['guild'],'live','ingest',{'session':o['session'],'events':events})))
                if o['once']:break
                time.sleep(.5)
        except KeyboardInterrupt:self.stdout.write('Capture stopped. Session can be saved from the dashboard.')
