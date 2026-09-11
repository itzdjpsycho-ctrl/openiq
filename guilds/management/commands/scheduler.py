import signal,threading
from django.core.management.base import BaseCommand
from django.core.management import call_command
class Command(BaseCommand):
    help='Run local scheduled jobs continuously; notifications remain previews.'
    def add_arguments(self,p):p.add_argument('--interval',type=int,default=30)
    def handle(self,*args,**o):
        stop=threading.Event()
        for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,lambda *_:stop.set())
        while not stop.is_set():
            try:call_command('tick',stdout=self.stdout)
            except Exception as exc:self.stderr.write('Scheduled run failed: '+str(exc))
            stop.wait(max(1,o['interval']))
