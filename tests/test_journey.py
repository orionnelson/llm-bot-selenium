"""Public URL boundaries and instruction-DAG worker; deterministic fake browser/model."""
import json
import os
from pathlib import Path
from socket import getaddrinfo
import tempfile
from threading import Lock
import unittest
from unittest.mock import patch

from triage.browser_loop import BrowserRuns
from triage.journey import definition, propose_step, start_journey, OBSERVE_PUBLIC
from triage.public_browser import public_url
from triage.dag import DAG
from test_browser_loop import png
from test_dag_server import backend, request

PUBLIC = [(2, 1, 6, '', ('34.134.219.254', 443))]

class Element:
    def __init__(self, driver): self.driver = driver
    def is_displayed(self): return True
    def is_enabled(self): return True
    def click(self): self.driver.clicked = True

class Driver:
    def __init__(self): self.current_url='about:blank'; self.clicked=False; self.quits=0
    def execute_cdp_cmd(self, *args): return {'arguments': ['--headless=new']}
    def set_window_size(self,*args): pass
    def set_page_load_timeout(self,*args): pass
    def set_script_timeout(self,*args): pass
    def get(self,url): self.current_url=url
    def quit(self): self.quits+=1
    def find_element(self,*args): return Element(self)
    def get_screenshot_as_png(self): return png()
    def execute_script(self,script,*args):
        if script==OBSERVE_PUBLIC:
            return {'url':self.current_url,'documentUri':self.current_url,'title':'Public test','text':'Projects Security News '+('CyberScoop 10 Articles' if self.clicked else ''),'candidates':[{'id':'c0','label':'Projects','kind':'heading','href':None,'expanded':None},{'id':'c1','label':'Security News','kind':'control','href':'javascript:void(0);','expanded':None}], 'facts':[{'id':'f0','label':'CyberScoop','count':10,'text':'CyberScoop 10 Articles'}] if self.clicked else []}
        return None

class JourneyTests(unittest.TestCase):
    @patch('triage.public_browser.socket.getaddrinfo', return_value=PUBLIC)
    def test_public_urls_reject_private_credentials_and_bad_schemes(self, dns):
        self.assertEqual(public_url('https://or9.ca/'), 'https://or9.ca/')
        for value in ['file:///etc/passwd','http://localhost/','http://127.0.0.1/','http://169.254.169.254/','http://airflow.llms.svc.cluster.local/','https://user:pass@or9.ca/','https://or9.ca:8080/','https://or9.ca/?token=secret','https://or9.ca/?%74oken=secret','http://224.0.0.1/','https://or9.ca/\\evil']:
            with self.subTest(value=value),self.assertRaises((ValueError,OSError)):public_url(value)
        dns.return_value=[(2,1,6,'',('10.0.0.1',443))]
        with self.assertRaises(ValueError):public_url('https://public-looking.example/')

    def test_each_instruction_is_a_valid_sequential_dag_task(self):
        plan=definition('https://or9.ca/',['Find Projects','Click News','Screenshot article counts'])
        dag=DAG.from_spec(plan);dag.validate()
        self.assertEqual([t.task_id for t in dag.tasks],['start','navigate','step-1','step-2','step-3','end'])
        self.assertEqual(dag.tasks[3].depends_on,('step-1',))
        self.assertEqual(dag.tasks[4].params['prompt'],'Screenshot article counts')

    @patch('triage.public_browser.socket.getaddrinfo', return_value=PUBLIC)
    @patch('triage.journey.grid_status', return_value={'ready':True})
    def test_complete_public_journey_records_steps_counts_and_cleanup(self,*_):
        driver=Driver()
        def propose(instruction,observation):
            action='finish' if observation['completedActions'] or 'Screenshot' in instruction else 'click' if 'Click' in instruction else 'scroll'
            return {'action':action,'candidate':None if action=='finish' else 'c1' if action=='click' else 'c0','evidence':observation['evidence'],'result':'Untrusted model total:999'}
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'SELENIUM_GRID_URL':'http://grid:4444'}),patch('triage.journey.propose_step',side_effect=propose):
            manager=BrowserRuns(Path(directory),Lock(),lambda:'revision',driver_factory=lambda url:driver,evidence_kind='simulated')
            queued=start_journey(manager,'https://or9.ca/',['Find Projects','Click News','Screenshot article counts'])
            self.assertTrue(manager.generation_lock.acquire(timeout=5));manager.generation_lock.release()
            value=manager.read(queued['id'])
            self.assertEqual(value['status'],'passed',value)
            self.assertEqual([s['id'] for s in value['steps']],['navigate','step-1','step-2','step-3'])
            self.assertTrue(all(s['state']=='verified' for s in value['steps']))
            self.assertEqual(value['steps'][-1]['facts'][0]['count'],10)
            self.assertEqual(value['steps'][-1]['result'],'CyberScoop: 10 articles')
            self.assertEqual(value['steps'][-1]['screenshots'][0]['count'],10)
            self.assertEqual(len(value['frames']),len(value['frameTimesMs']))
            self.assertFalse(value['sessionActive']);self.assertEqual(driver.quits,1)
            self.assertEqual(value['triage']['events'][1]['action'],'click')
            for name in value['frames']:self.assertEqual((Path(directory)/value['id']/name.rsplit('/',1)[1]).stat().st_mode&0o077,0)

    def test_model_cannot_invent_controls_actions_or_evidence(self):
        observation={'evidence':'hash','candidates':[{'id':'c0','kind':'control','label':'Delete account'}]}
        for proposed in [{'action':'click','candidate':'missing','evidence':'hash','result':''},{'action':'click','candidate':'c0','evidence':'hash','result':''},{'action':'finish','candidate':None,'evidence':'other','result':''},{'action':'execute','candidate':'c0','evidence':'hash','result':''}]:
            with patch('triage.journey.complete',return_value=json.dumps(proposed)),self.assertRaises(ValueError):propose_step('Inspect',observation)

    @patch('triage.public_browser.socket.getaddrinfo', side_effect=lambda host, *args, **kwargs:
           getaddrinfo(host, *args, **kwargs) if host == '127.0.0.1' else PUBLIC)
    def test_api_rejects_internal_url_and_bounded_bad_instructions_without_execution(self,*_):
        with backend(test_mode=True) as (port,_,_):
            for body in [{'url':'http://localhost/','steps':['inspect']},{'url':'https://or9.ca/','steps':[]},{'url':'https://or9.ca/','steps':['']},{'url':'https://or9.ca/','steps':['inspect']*9}]:
                code,_=request(port,'POST',json.dumps(body),{'Content-Type':'application/json'},'/api/browser/journeys');self.assertEqual(code,400)

class CoderModelSelectionTests(unittest.TestCase):
    def test_explicit_coder_is_not_shadowed_by_model_catalog_iteration(self):
        from triage.test_codegen import complete
        from triage.journey import CODER
        requests=[]
        def smol(path,payload=None):
            requests.append((path,payload))
            if path=='/v1/models':return {'data':[{'id':CODER,'status':{'value':'unloaded'}},{'id':'other','status':{'value':'loaded'}}]}
            if path=='/v1/chat/completions':return {'model':CODER,'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]}
            return {}
        with patch('triage.test_codegen.smol',side_effect=smol),patch('triage.test_codegen.wait_model'):
            self.assertEqual(complete([],model=CODER),'{}')
        self.assertIn(('/models/load',{'model':CODER}),requests)
        self.assertEqual(next(p for path,p in requests if path=='/v1/chat/completions')['model'],CODER)

class RequestInterceptionTests(unittest.TestCase):
    def test_every_subresource_is_filtered_and_private_redirects_are_failed_closed(self):
        from queue import Queue, Empty
        import websocket
        from threading import Event
        from triage.public_browser import PublicRequests
        class Socket:
            def __init__(self):self.queue=Queue();self.sent=[];self.action=Event()
            def send(self,raw):
                value=json.loads(raw);self.sent.append(value)
                method=value['method'];result={'targetInfos':[{'type':'page','targetId':'page'}]} if method=='Target.getTargets' else {'sessionId':'attached'} if method=='Target.attachToTarget' else {}
                self.queue.put(json.dumps({'id':value['id'],'result':result}))
                if method in ('Fetch.continueRequest','Fetch.failRequest'):self.action.set()
            def recv(self):
                try:return self.queue.get(timeout=.1)
                except Empty:raise websocket.WebSocketTimeoutException()
            def close(self):self.queue.put('')
        socket=Socket()
        with patch('websocket.create_connection',return_value=socket),patch('triage.public_browser.socket.getaddrinfo',return_value=PUBLIC):
            guard=PublicRequests(type('Driver',(),{'capabilities':{'se:cdp':'ws://grid/session/own/se/cdp'},'execute_cdp_cmd':lambda *args:{'targetInfo':{'type':'page','targetId':'page'}}})())
            for url,expected in [('https://or9.ca/','Fetch.continueRequest'),('http://127.0.0.1/','Fetch.failRequest'),('http://10.96.0.1/','Fetch.failRequest'),('ftp://or9.ca/file','Fetch.failRequest')]:
                socket.action.clear();socket.queue.put(json.dumps({'method':'Fetch.requestPaused','sessionId':'attached','params':{'requestId':'request','request':{'url':url}}}))
                self.assertTrue(socket.action.wait(2));self.assertEqual(socket.sent[-1]['method'],expected)
            guard.close()
        self.assertIn('Fetch.enable',[command['method'] for command in socket.sent])
