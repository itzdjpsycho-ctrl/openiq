#!/usr/bin/env python3
"""Companion capture prototype: stream a normalized JSONL file over authenticated HTTP.

No packet decoding is implied. Run on a desktop with Python's tkinter installed.
"""
import json,queue,threading,time,tkinter as tk
from tkinter import ttk,filedialog,messagebox
from urllib.request import build_opener,HTTPCookieProcessor,Request
from urllib.parse import urlencode
from http.cookiejar import CookieJar
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from guilds.capture import JsonLineTail

class App:
    def __init__(self,root):
        self.root=root;root.title('Observatory Capture · file adapter');root.geometry('560x440');self.fields={};self.stop=threading.Event();self.events=queue.Queue()
        ttk.Label(root,text='Local combat-event capture',font=('',18)).pack(pady=15)
        ttk.Label(root,text='Prototype file adapter — does not decode BDO packets.').pack()
        form=ttk.Frame(root);form.pack(fill='x',padx=25,pady=15)
        for name,value in [('Server','http://127.0.0.1:8000'),('Username','demo'),('Password',''),('Guild ID','1'),('Title','Local capture')]:
            row=ttk.Frame(form);row.pack(fill='x',pady=3);ttk.Label(row,text=name,width=12).pack(side='left');entry=ttk.Entry(row,show='*' if name=='Password' else '');entry.insert(0,value);entry.pack(side='right',fill='x',expand=True);self.fields[name]=entry
        ttk.Button(root,text='Open event file and start',command=self.start).pack(pady=5);ttk.Button(root,text='Save & Stop',command=self.stop.set).pack(pady=5)
        self.status=ttk.Label(root,text='Ready');self.status.pack(pady=10);root.after(200,self.poll)
    def start(self):
        if hasattr(self,'worker') and self.worker.is_alive():return
        filename=filedialog.askopenfilename(filetypes=[('Event log','*.jsonl'),('All files','*')])
        if not filename:return
        values={k:v.get() for k,v in self.fields.items()};self.stop.clear();self.worker=threading.Thread(target=self.run,args=(filename,values),daemon=True);self.worker.start()
    def poll(self):
        while not self.events.empty():self.status.configure(text=self.events.get())
        self.root.after(200,self.poll)
    def run(self,filename,v):
        try:
            base=v['Server'].rstrip('/');jar=CookieJar();client=build_opener(HTTPCookieProcessor(jar));client.open(base+'/login/',timeout=10).read()
            def csrf():return next(c.value for c in jar if c.name=='csrftoken')
            data=urlencode({'username':v['Username'],'password':v['Password'],'csrfmiddlewaretoken':csrf()}).encode();client.open(Request(base+'/login/',data=data,headers={'Referer':base+'/login/'}),timeout=10).read()
            def post(action,payload):
                request=Request(base+f"/api/{int(v['Guild ID'])}/live/{action}/",data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-CSRFToken':csrf(),'Referer':base+'/'})
                response=json.load(client.open(request,timeout=15))
                if not response.get('ok'):raise ValueError(response)
                return response['result']
            session=post('start',{'title':v['Title']});tail=JsonLineTail(filename);count=0
            while not self.stop.is_set():
                events=tail.read()
                if events:result=post('ingest',{'session':session['id'],'events':events});count=result['total']
                self.events.put(f'Connected · {count} events');self.stop.wait(.5)
            post('stop',{'session':session['id']});self.events.put(f'Saved · {count} events')
        except Exception as exc:self.events.put('Error: '+str(exc))
if __name__=='__main__':root=tk.Tk();App(root);root.mainloop()
