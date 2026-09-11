"""Local event-file adapter; preserves incomplete lines and handles file rotation.

This is a prototype transport, not a claim to decode BDO network packets.
"""
import hashlib,json
from pathlib import Path

class JsonLineTail:
    def __init__(self,path):self.path=Path(path);self.offset=0;self.inode=None;self.pending=b''
    def read(self):
        stat=self.path.stat()
        if self.inode!=stat.st_ino or stat.st_size<self.offset:self.offset=0;self.pending=b'';self.inode=stat.st_ino
        with self.path.open('rb') as file:file.seek(self.offset);chunk=file.read();self.offset=file.tell()
        lines=(self.pending+chunk).split(b'\n');self.pending=lines.pop();events=[]
        for line in lines:
            if not line.strip():continue
            event=json.loads(line.decode('utf-8'));event.setdefault('id',hashlib.sha256(line).hexdigest());events.append(event)
        return events
