"""Ensure extractor-style blank descriptions reach the actual backend protocol."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.request
import urllib.error
from port_station.assets import make_catalog
from port_station.project import WORKSPACE,read_project

SERVER=WORKSPACE/'build/prospero-achievements/host/prospero_achievements.exe'

class CatalogTests(unittest.TestCase):
    def project(self):
        p=read_project(WORKSPACE/'port_station/examples/tcoaal.ps5port.json')
        p.update(game_id='own.empty-description',title='Own catalog fixture',adapter='file-v1',platinum=True,platinum_description='')
        p['achievements']=[dict(id='FIRST',source_id='FIRST',title='First',description='',icon='',target=1,hidden=False)]
        return p
    def test_display_fallback_does_not_invent_source_metadata(self):
        p=self.project();before=deepcopy(p)
        with tempfile.TemporaryDirectory()as td:
            catalog,_,_=make_catalog(p,WORKSPACE/'port_station/examples',Path(td))
            self.assertEqual(p,before)
            self.assertTrue(all(a['description']=='Descrição não informada.'for a in catalog['achievements']))
    @unittest.skipUnless(SERVER.is_file(),'Requires the host backend from the Windows kit')
    def test_actual_backend_accepts_generated_catalog_and_rejects_raw_empty_description(self):
        p=self.project()
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);catalog,resources,blob=make_catalog(p,WORKSPACE/'port_station/examples',root/'catalog')
            with socket.socket()as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
            server=subprocess.Popen([str(SERVER),str(root/'state'),str(port)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            def request(method,path,data=None):
                req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=data,method=method)
                try:
                    with urllib.request.urlopen(req,timeout=3)as response:return response.status,response.read()
                except urllib.error.HTTPError as error:return error.code,error.read()
            try:
                for _ in range(80):
                    try:
                        if request('GET','/api/v1/info')[0]==200:break
                    except OSError:time.sleep(.05)
                raw=deepcopy(catalog);raw['achievements'][0]['description']=''
                self.assertEqual(request('POST','/api/v1/catalogs',json.dumps(raw).encode())[0],400)
                for digest,data in resources.items():self.assertIn(request('PUT','/api/v1/assets/'+digest+'.png',data)[0],(200,201))
                self.assertEqual(request('POST','/api/v1/catalogs',blob)[0],201)
                games=json.loads(request('GET','/api/v1/games')[1])['games']
                self.assertEqual(len(games[0]['achievements']),2)
            finally:server.terminate();server.wait(timeout=5)

if __name__=='__main__':unittest.main()
