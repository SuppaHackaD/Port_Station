"""End-to-end host tests of the actual C service and SDK, using private fixtures."""
from pathlib import Path
from copy import deepcopy
import hashlib,http.client,http.server,json,os,socket,struct,subprocess,tempfile,threading,time,urllib.error,urllib.request,zlib
R=Path(__file__).resolve().parents[1];W=R/'build/prospero-achievements';S=W/'host/prospero_achievements.exe';PROBE=W/'host/pa_sdk_probe.exe'
run=Path(tempfile.mkdtemp(prefix='run-',dir=W));root=run/'service';outbox=run/'outbox'
flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
build=json.loads((W/'build.json').read_text())
for name,digest in build['sources'].items():
    assert hashlib.sha256((R/name).read_bytes()).hexdigest()==digest,'Build is stale: '+name
for name,digest in build['host_artifacts'].items():
    assert hashlib.sha256((W/'host'/name).read_bytes()).hexdigest()==digest,'Host binary differs: '+name
checks=[];process=None;logs=[]
def check(ok,name):
    assert ok,name
    checks.append(name);print('PASS',name,flush=True)
def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
PORT=port()
def request(method,path,body=None,headers=None):
    data=json.dumps(body,ensure_ascii=False).encode() if isinstance(body,dict) else body
    req=urllib.request.Request('http://127.0.0.1:'+str(PORT)+path,data=data,method=method,headers=headers or {})
    try:
        with urllib.request.urlopen(req,timeout=5) as r:return r.status,r.read()
    except urllib.error.HTTPError as e:return e.code,e.read()
def api(method,path,body=None,headers=None):
    code,b=request(method,'/api/v1/'+path,body,headers)
    return code,json.loads(b)
def start():
    global process
    log=(run/f'server-{len(logs)}.log').open('wb');logs.append(log)
    process=subprocess.Popen([str(S),str(root),str(PORT)],stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        try:
            code,info=api('GET','info')
            if code==200:return info
        except OSError:pass
        if process.poll() is not None:raise AssertionError('server exited: '+str(process.returncode))
        time.sleep(.05)
    raise AssertionError('server did not listen')
def stop():
    global process
    if process:
        process.terminate();process.wait(timeout=5);process=None
def probe(folder=outbox,p=PORT):
    return subprocess.run([str(PROBE),str(folder),str(p)],capture_output=True,text=True,timeout=20,creationflags=flags)
def state(user='00000001'):
    code,j=api('GET','state/'+user+'/sdk.lifecycle.test');assert code==200,j
    return {a['id']:a for a in j['achievements']},j
try:
    directory=subprocess.run([str(W/'host/pa_directory_test.exe')],capture_output=True,text=True,timeout=10,creationflags=flags)
    check(directory.returncode==0,'PS5 getdents record decoder validates bounds, names, large blocks and capacity')
    p=probe()
    check(p.returncode==4 and len(list((outbox/'pending').glob('*.json')))==2,'SDK keeps durable outbox when service is absent')
    first=start();check(first['api_major']==1 and first['version']=='0.1.0','actual C server health/protocol')
    p=probe();check(p.returncode==0 and not list((outbox/'pending').glob('*.json')),'native SDK uploads catalog/assets and acknowledges queued events')
    s,j=state();check(s['HELLO']['unlocked'] and s['PROGRESS']['progress']==1 and not s['ALL']['unlocked'] and j['event_count']==2,'state reflects unlock, partial progress and locked completion')
    catalog=api('GET','games')[1]['games'][0];icon=catalog['icon']
    check(api('POST','catalogs',dict(catalog,game_id='SDK.lifecycle.test'))[0]==400,'lowercase game IDs prevent case-collision across filesystems')
    check(hashlib.sha256(request('GET','/api/v1/assets/'+icon+'.png')[1]).hexdigest()==icon,'uploaded icon uses correct SHA-256 and round-trips')
    p=probe();check(p.returncode==0 and state()[1]['event_count']==2,'SDK replays are idempotent across client restarts')
    event={'event_id':'finish-v1','game_id':'sdk.lifecycle.test','user_id':'00000001','achievement_id':'PROGRESS','type':'progress','value':3}
    code,j=api('POST','events',event);check(code==201 and set(j['new_unlocks'])=={'PROGRESS','ALL'},'progress threshold and completion awarded in one durable transaction')
    date=state()[0]['ALL']['unlocked_at']
    code,j=api('POST','events',dict(reversed(list(event.items()))));check(code==200 and j['status']=='duplicate' and not j['new_unlocks'],'semantic replay with reordered JSON keys does not duplicate unlocks')
    conflict=dict(event,value=2);check(api('POST','events',conflict)[0]==409,'same event ID with different contents rejected')
    check(api('POST','events',dict(event,event_id='low-v1',value=0))[0]==201 and state()[0]['PROGRESS']['progress']==3,'progress never regresses')
    check(api('POST','events',dict(event,event_id='meta-direct',achievement_id='ALL',type='unlock'))[0]==400,'game cannot directly grant the calculated completion award')
    code,_=api('POST','events',dict(event,event_id='user2',user_id='00000002',achievement_id='HELLO',type='unlock'))
    check(code==201 and not state('00000002')[0]['ALL']['unlocked'],'users have separate progress')
    check(api('POST','events',dict(event,user_id='../escape'))[0]==400,'path-like user identifiers rejected')
    check(api('POST','events',dict(event,event_id='bad-ach',achievement_id='UNKNOWN'))[0]==400,'unknown achievement rejected')
    check(api('POST','events',event,{'Origin':'http://example.invalid'})[0]==403,'browser-origin mutation rejected; web is read-only')
    check(request('GET','/api/v2/info')[0]==404,'unsupported API route does not silently succeed')
    duplicate=b'{"game_id":"sdk.lifecycle.test","game_id":"other"}'
    check(api('POST','events',duplicate)[0]==400,'duplicate JSON keys rejected')
    nul=json.dumps(dict(event,event_id='foo\x00bar')).encode()
    check(api('POST','events',nul)[0]==400,'embedded decoded NUL rejected')
    bad_utf8=json.dumps(dict(catalog,catalog_version=3)).encode().replace(json.dumps(catalog['title']).encode(),b'"\xc0\xaf"',1)
    check(api('POST','catalogs',bad_utf8)[0]==400,'invalid UTF-8 rejected before persistence')
    altered=deepcopy(catalog);altered['title']='Título atualizado'
    check(api('POST','catalogs',altered)[0]==409,'catalog changes require increased version')
    altered['catalog_version']=2;altered['achievements'].append({'id':'EXTRA','title':'Mais uma','description':'Nova definição sem apagar desbloqueios.','target':1})
    check(api('POST','catalogs',altered)[0]==201,'catalog can add definitions without resetting existing progress')
    code,j=api('POST','catalogs',catalog)
    check(code==200 and j['status']=='newer_catalog_active' and api('GET','games')[1]['games'][0]['catalog_version']==2,'older compatible game build can send events without downgrading newer metadata')
    s,_=state();check(s['ALL']['unlocked'] and s['ALL']['unlocked_at']==date and not s['EXTRA']['unlocked'],'previous completion remains obtained after catalog grows')
    destructive=deepcopy(altered);destructive['catalog_version']=3;destructive['achievements'][0]['target']=2
    check(api('POST','catalogs',destructive)[0]==409,'existing condition changes require explicit migration')
    before=root/'users/00000001/sdk.lifecycle.test.journal'
    old=before.read_bytes();stop();restarted=start()
    check(restarted['instance_id']!=first['instance_id'] and state()[0]['ALL']['unlocked'],'state and dates survive abrupt service restart')
    with before.open('ab') as f:f.write(b'\x10\x00\x00')
    size=before.stat().st_size
    check(state()[1]['incomplete_tail'] and before.stat().st_size==size,'read exposes incomplete tail without changing storage')
    e=dict(event,event_id='after-torn-tail',achievement_id='EXTRA',type='unlock')
    check(api('POST','events',e)[0]==201 and not state()[1]['incomplete_tail'],'next valid transaction recovers only an incomplete trailing write')
    bad=root/'users/00000002/sdk.lifecycle.test.journal';b=bytearray(bad.read_bytes());b[-1]^=1;bad.write_bytes(b);digest=hashlib.sha256(b).hexdigest()
    check(api('GET','state/00000002/sdk.lifecycle.test')[0]==503,'complete record with wrong checksum is rejected')
    check(api('POST','events',dict(e,user_id='00000002'))[0]==503 and hashlib.sha256(bad.read_bytes()).hexdigest()==digest,'corrupt journal preserved instead of overwritten')
    check(api('PUT','assets/'+'0'*64+'.png',(W/'sdk-test-icon.png').read_bytes())[0]==400,'image content hash mismatch rejected')
    check(api('PUT','assets/'+hashlib.sha256(b'not png').hexdigest()+'.png',b'not png')[0]==400,'non-PNG upload rejected')
    other=subprocess.run([str(S),str(root),str(port())],capture_output=True,timeout=5,creationflags=flags)
    check(other.returncode==4 and api('GET','info')[1]['instance_id']==restarted['instance_id'],'single writer lock prevents another service using the same root')
    page=request('GET','/')[1];js=request('GET','/app.js')[1]
    check(b'Prospero Achievements' in page and b'textContent' in js and b'innerHTML' not in js,'embedded web and DOM text rendering delivered by the ELF code')
    # Raw header ambiguity must be rejected before any event is processed.
    con=http.client.HTTPConnection('127.0.0.1',PORT,timeout=5)
    con.putrequest('POST','/api/v1/events');con.putheader('Content-Length','0');con.putheader('Content-Length','0');con.endheaders()
    res=con.getresponse();res.read();check(res.status==400,'ambiguous duplicate Content-Length rejected');con.close()
    # A client never discards an event merely because a response is HTTP 201.
    class Fake(http.server.BaseHTTPRequestHandler):
        major=1
        def log_message(self,*a):pass
        def do_GET(self):self.reply({'service':'prospero_achievements','api_major':self.major,'instance_id':'fake-v1'})
        def do_PUT(self):self.rfile.read(int(self.headers.get('Content-Length','0')));self.reply({},201)
        def do_POST(self):
            self.rfile.read(int(self.headers.get('Content-Length','0')))
            self.reply({'status':'accepted','event_id':'wrong-event-id'},201)
        def reply(self,j,code=200):
            b=json.dumps(j).encode();self.protocol_version='HTTP/1.1';self.send_response(code);self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    fake=http.server.HTTPServer(('127.0.0.1',0),Fake);thread=threading.Thread(target=fake.serve_forever,daemon=True);thread.start()
    p=probe(run/'wrong-ack',fake.server_port)
    check(p.returncode==4 and len(list((run/'wrong-ack/pending').glob('*.json')))==2,'SDK retains events when server acknowledgement has the wrong event ID')
    Fake.major=2;p=probe(run/'wrong-version',fake.server_port)
    check(p.returncode==4 and len(list((run/'wrong-version/pending').glob('*.json')))==2,'SDK refuses incompatible protocol major and keeps outbox')
    fake.shutdown();fake.server_close()
    code,j=api('POST','service/stop',b'');process.wait(timeout=5)
    check(code==200 and j['status']=='stopping' and process.returncode==0,'local control request stops only this service cleanly')
    process=None
    result={'status':'passed','checks':checks,'count':len(checks),'fixtures':str(run),'scope':'actual C Windows host service and SDK; PS5 lifecycle remains untested'}
    (W/'host-tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'passed','checks':len(checks),'fixtures':str(run)}),flush=True)
finally:
    stop()
    for log in logs:log.close()
