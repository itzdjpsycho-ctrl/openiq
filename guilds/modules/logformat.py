"""Independent decoder for the public IKUSA text record contract.

Contract observed from CritIQ's publicly served log-import interface:
[HH:MM:SS] <local character> has killed|died to <enemy> from <guild>
Optional suffix: (<local family>, <enemy family>).
"""
import hashlib
from datetime import datetime,timedelta,timezone
from .core import Invalid,date

def parse_log(text,day,offset='+00:00'):
    current=datetime.fromisoformat(date(day)+'T00:00:00'+offset)
    if current.tzinfo is None:raise Invalid('Log timezone offset is required')
    previous=None;result=[]
    for index,line in enumerate(text.splitlines()):
        line=line.strip()
        if not line:continue
        if not line.startswith('[') or ']' not in line:raise Invalid(f'Line {index+1}: missing timestamp')
        clock,body=line[1:].split(']',1)
        try:hour,minute,second=map(int,clock.split(':'));stamp=current.replace(hour=hour,minute=minute,second=second)
        except ValueError:raise Invalid(f'Line {index+1}: invalid time')
        if previous and stamp<previous:
            if (previous-stamp).total_seconds()>12*3600:current+=timedelta(days=1);stamp+=timedelta(days=1)
            else:raise Invalid(f'Line {index+1}: timestamps are out of order')
        previous=stamp
        if ' has killed ' in body:local,rest=body.split(' has killed ',1);kind='kill'
        elif ' died to ' in body:local,rest=body.split(' died to ',1);kind='death'
        else:raise Invalid(f'Line {index+1}: unsupported combat message')
        if ' from ' not in rest:raise Invalid(f'Line {index+1}: missing enemy guild')
        enemy,guild=rest.rsplit(' from ',1);family='';local_family=''
        if guild.endswith(')') and ' (' in guild:
            guild,suffix=guild.rsplit(' (',1);families=[x.strip() for x in suffix[:-1].split(',')];local_family=families[0] if families else '';family=families[1] if len(families)>1 else ''
        local=local.strip();enemy=enemy.strip()
        if not local or not enemy or not guild.strip():raise Invalid(f'Line {index+1}: incomplete combat event')
        result.append({'id':hashlib.sha256((day+'|'+str(index)+'|'+line).encode()).hexdigest(),'at':stamp.astimezone(timezone.utc).isoformat(),'kind':kind,'player':local if kind=='kill' else enemy,'target':enemy if kind=='kill' else local,'guild':guild.strip(),'family':family,'local_family':local_family,'class':'Unknown'})
    if not result:raise Invalid('No combat events found')
    return result
