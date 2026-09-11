"""Generate actual PCAP frames and exercise segmentation, flows and retransmits."""
import os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from guilds.packets import Calibration,StreamDecoder
from scapy.layers.inet import IP,TCP
from scapy.layers.l2 import Ether
from scapy.packet import Raw
from scapy.utils import wrpcap,PcapReader
root=Path(__file__).resolve().parents[1];c=Calibration.load(root/'fixtures/calibration-historical.json')
def record(kill=True):
    raw=bytearray(c.record_bytes);raw[:len(c.marker)]=c.marker
    for key,name in [('guild','Moonfall'),('local','Aster'),('enemy','Opponent')]:
        encoded=name.encode(c.encoding);offset=c.fields[key];raw[offset:offset+len(encoded)]=encoded
    raw[c.kill_nibble//2]=1 if kill else 0
    return bytes(raw)
def packet(data,seq,port=55000):
    p=Ether(src='02:00:00:00:00:01',dst='02:00:00:00:00:02')/IP(src='203.0.113.5',dst='192.0.2.10')/TCP(sport=8888,dport=port,seq=seq,flags='PA')/Raw(data);p.time=1789117200;return p
raw=record();packets=[packet(raw[:100],1000),packet(raw[200:],1200),packet(raw[100:200],1100),packet(raw,1000),packet(record(False),5000,55001)]
with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/'synthetic.pcap';wrpcap(str(path),packets);d=StreamDecoder(c);events=[]
    with PcapReader(str(path)) as reader:
        for p in reader:events.extend(d.packet(p))
    assert len(events)==2,events
    assert events[0]['kind']=='kill' and events[0]['player']=='Aster'
    assert events[1]['kind']=='death' and events[1]['target']=='Aster'
    print('PCAP decoder passed: split records, out-of-order segments, retransmit deduplication, independent TCP streams and kill/death orientation.')
    if '--save-fixture' in sys.argv:wrpcap(str(root/'fixtures/combat-synthetic.pcap'),packets)
