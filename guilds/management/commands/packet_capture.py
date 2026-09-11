import json
from django.core.management.base import BaseCommand,CommandError
from django.contrib.auth.models import User
from guilds.packets import Calibration,StreamDecoder
from guilds.services import execute
class Command(BaseCommand):
    help='Decode an offline PCAP or explicitly selected live interfaces using supplied calibration.'
    def add_arguments(self,p):
        p.add_argument('--calibration',required=True);source=p.add_mutually_exclusive_group(required=True);source.add_argument('--pcap');source.add_argument('--interfaces',nargs='+');p.add_argument('--output');p.add_argument('--session');p.add_argument('--guild',type=int,default=1);p.add_argument('--user',default='demo');p.add_argument('--seconds',type=int,default=60)
    def handle(self,*args,**o):
        from scapy.layers.inet import IP,TCP  # Register protocols before packets are read.
        decoder=StreamDecoder(Calibration.load(o['calibration']));self.stderr.write('Calibration: '+decoder.calibration.patch)
        user=User.objects.get(username=o['user']) if o['session'] else None
        output=open(o['output'],'a',encoding='utf-8') if o['output'] else None;count=0
        def consume(packet):
            nonlocal count
            events=decoder.packet(packet)
            if events and user:execute(user,o['guild'],'live','ingest',{'session':o['session'],'events':events})
            for event in events:
                count+=1;line=json.dumps(event)
                if output:output.write(line+'\n');output.flush()
                else:self.stdout.write(line)
        try:
            if o['pcap']:
                from scapy.layers.l2 import Ether  # Register Ethernet PCAP link type.
                from scapy.utils import PcapReader
                with PcapReader(o['pcap']) as reader:
                    for packet in reader:consume(packet)
            else:
                from scapy.sendrecv import sniff
                sniff(iface=o['interfaces'],filter='tcp',prn=consume,store=False,timeout=o['seconds'])
        except (OSError,ValueError) as exc:raise CommandError(str(exc))
        finally:
            if output:output.close()
        self.stderr.write(f'Decoded {count} events; rejected {decoder.bad_records} invalid records.')
