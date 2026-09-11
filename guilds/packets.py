"""Independent calibrated combat decoder with per-flow TCP assembly.

Packet field locations are configuration, never inferred from unrelated traffic.
The provided calibration is historical; current BDO compatibility is unverified.
"""
from dataclasses import dataclass
from datetime import datetime,timezone
import hashlib,ipaddress,json
from pathlib import Path

@dataclass(frozen=True)
class Calibration:
    marker:bytes
    record_bytes:int
    fields:dict
    name_bytes:int
    kill_nibble:int
    networks:tuple
    encoding:str='utf-16-le'
    patch:str='unknown'
    @classmethod
    def load(cls,path):
        data=json.loads(Path(path).read_text());marker=bytes.fromhex(data['marker']);length=int(data['record_bytes']);name_bytes=int(data['name_bytes']);nibble=int(data['kill_nibble']);fields=data['fields']
        if not marker or not 1<=length<=65536 or not 1<=name_bytes<=1024:raise ValueError('Invalid calibration lengths')
        if nibble<0 or nibble//2>=length:raise ValueError('Kill field outside record')
        if set(fields)!={'local','enemy','guild'} or any(not isinstance(v,int) or v<0 or v+name_bytes>length for v in fields.values()):raise ValueError('Name fields outside record')
        networks=tuple(ipaddress.ip_network(n) for n in data['server_networks'])
        if not networks:raise ValueError('Choose explicit server networks')
        return cls(marker,length,fields,name_bytes,nibble,networks,data.get('encoding','utf-16-le'),str(data.get('patch','unknown')))

class StreamDecoder:
    def __init__(self,calibration):self.calibration=calibration;self.flows={};self.bad_records=0
    def feed(self,flow,sequence,payload,at):
        if not payload:return []
        c=self.calibration
        state=self.flows.setdefault(flow,{'next':sequence,'buffer':b'','pending':{}})
        if sequence<state['next']:
            overlap=state['next']-sequence
            if overlap>=len(payload):return []
            payload=payload[overlap:];sequence=state['next']
        if sequence>state['next']:
            if len(state['pending'])<128:state['pending'][sequence]=payload
            return []
        state['buffer']+=payload;state['next']+=len(payload)
        while state['next'] in state['pending']:
            chunk=state['pending'].pop(state['next']);state['buffer']+=chunk;state['next']+=len(chunk)
        result=[]
        while True:
            start=state['buffer'].find(c.marker)
            if start<0:
                state['buffer']=state['buffer'][-max(len(c.marker)-1,0):] if len(c.marker)>1 else b'';break
            state['buffer']=state['buffer'][start:]
            if len(state['buffer'])<c.record_bytes:break
            record=state['buffer'][:c.record_bytes];state['buffer']=state['buffer'][c.record_bytes:]
            try:
                fields={key:record[offset:offset+c.name_bytes].decode(c.encoding,errors='strict').split('\x00',1)[0].strip() for key,offset in c.fields.items()}
                if any(not name or any(ord(ch)<32 for ch in name) for name in fields.values()):raise ValueError('Invalid name field')
                byte=record[c.kill_nibble//2];nibble=byte&15 if c.kill_nibble%2 else byte>>4
                if nibble not in [0,1]:raise ValueError('Invalid kill flag')
                kill=nibble==1
                # Include stream sequence position so repeated legitimate identical kills remain distinct.
                position=state['next']-len(state['buffer'])-c.record_bytes
                eid=hashlib.sha256(repr((flow,position)).encode()+record).hexdigest()
                result.append({'id':eid,'at':datetime.fromtimestamp(float(at),timezone.utc).isoformat(),'kind':'kill' if kill else 'death','player':fields['local'] if kill else fields['enemy'],'target':fields['enemy'] if kill else fields['local'],'guild':fields['guild'],'class':'Unknown'})
            except (UnicodeDecodeError,ValueError):self.bad_records+=1
        if len(self.flows)>10000:self.flows.pop(next(iter(self.flows)))
        return result
    def packet(self,packet):
        from scapy.layers.inet import IP,TCP
        if IP not in packet or TCP not in packet:return []
        ip=packet[IP];tcp=packet[TCP]
        if not any(ipaddress.ip_address(ip.src) in network for network in self.calibration.networks):return []
        flow=(ip.src,int(tcp.sport),ip.dst,int(tcp.dport))
        if tcp.flags.S or tcp.flags.R:self.flows.pop(flow,None)
        return self.feed(flow,int(tcp.seq)+(1 if tcp.flags.S else 0),bytes(tcp.payload),packet.time)
