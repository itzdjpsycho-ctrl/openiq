"""Synthetic transport tests; no live interface or game account is used."""
import json,tempfile
from pathlib import Path
from django.test import SimpleTestCase
from .packets import Calibration,StreamDecoder

ROOT=Path(__file__).resolve().parents[1]
class PacketTests(SimpleTestCase):
    def setUp(self):self.c=Calibration.load(ROOT/'fixtures/calibration-historical.json')
    def record(self,kill=True):
        data=bytearray(self.c.record_bytes);data[:len(self.c.marker)]=self.c.marker
        for field,name in [('local','Alpha'),('enemy','Enemy'),('guild','Rival')]:
            encoded=name.encode(self.c.encoding);offset=self.c.fields[field];data[offset:offset+len(encoded)]=encoded
        data[self.c.kill_nibble//2]=int(kill)
        return bytes(data)
    def test_out_of_order_retransmits_and_legitimate_repeat(self):
        d=StreamDecoder(self.c);raw=self.record()
        self.assertEqual(d.feed('a',1000,raw[:100],0),[])
        self.assertEqual(d.feed('a',1200,raw[200:],0),[])
        first=d.feed('a',1100,raw[100:200],0)
        self.assertEqual(first[0]['player'],'Alpha')
        self.assertEqual(d.feed('a',1000,raw,0),[])
        second=d.feed('a',1300,raw,0)
        self.assertNotEqual(first[0]['id'],second[0]['id'])
        self.assertEqual(d.feed('b',1,self.record(False),0)[0]['target'],'Alpha')
    def test_overlapping_segment_and_split_marker(self):
        raw=self.record();d=StreamDecoder(self.c)
        self.assertEqual(d.feed('a',0,b'noise'+raw[:2],0),[])
        self.assertEqual(d.feed('a',5,raw,0)[0]['kind'],'kill')
        self.assertEqual(d.feed('a',305,b'',0),[])
    def test_bad_records_do_not_block_following_valid_record(self):
        raw=bytearray(self.record());raw[self.c.kill_nibble//2]=7
        d=StreamDecoder(self.c)
        self.assertEqual(len(d.feed('a',0,bytes(raw)+self.record(),0)),1)
        self.assertEqual(d.bad_records,1)
        raw=bytearray(self.record());offset=self.c.fields['local'];raw[offset:offset+self.c.name_bytes]=bytes(self.c.name_bytes)
        self.assertEqual(d.feed('b',0,bytes(raw),0),[]);self.assertEqual(d.bad_records,2)
    def test_calibration_rejects_invalid_boundaries(self):
        base=json.loads((ROOT/'fixtures/calibration-historical.json').read_text())
        for change in [{'marker':''},{'record_bytes':0},{'kill_nibble':600},{'fields':{'local':-1,'enemy':0,'guild':0}},{'server_networks':[]}]:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'calibration.json';path.write_text(json.dumps({**base,**change}))
                with self.assertRaises(ValueError):Calibration.load(path)
    def test_actual_pcap_fixture_and_source_filter(self):
        from scapy.utils import PcapReader
        from scapy.layers.inet import IP,TCP
        from scapy.packet import Raw
        d=StreamDecoder(self.c);events=[]
        with PcapReader(str(ROOT/'fixtures/combat-synthetic.pcap')) as reader:
            for packet in reader:events.extend(d.packet(packet))
        self.assertEqual([e['kind'] for e in events],['kill','death'])
        self.assertEqual(d.packet(Raw(b'not IP')),[])
        self.assertEqual(d.packet(IP(src='192.0.2.1')/TCP()/Raw(self.record())),[])
        packet=IP(src='203.0.113.5')/TCP(seq=1,flags='S')/Raw(self.record());packet.time=0
        self.assertEqual(len(d.packet(packet)),1)
