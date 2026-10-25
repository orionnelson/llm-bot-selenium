"""Generated code is interpreted as one grounded operation, never arbitrary Python."""
import json
import unittest
from unittest.mock import patch
from triage.browser_function import parse_function
from triage.journey import propose_step

class BrowserFunctionTests(unittest.TestCase):
    def test_generated_click_becomes_a_grounded_browser_operation(self):
        code='def run(browser):\n    browser.click("c1", "hash")'
        self.assertEqual(parse_function(code,'hash'),{'action':'click','candidate':'c1','evidence':'hash','python':code})
        observation={'evidence':'hash','candidates':[{'id':'c1','kind':'control','label':'News'}]}
        with patch('triage.journey.complete',return_value=json.dumps({'python':code,'result':'Open News'})):
            self.assertEqual(propose_step('Click News',observation)['python'],code)

    def test_normalizes_a_model_emitted_call_body_under_the_same_validation(self):
        parsed=parse_function('browser.click("c1", "hash")','hash')
        self.assertEqual(parsed['python'],'def run(browser):\n    browser.click("c1", "hash")')
        self.assertEqual(parsed['action'],'click')

    def test_rejects_arbitrary_code_imports_properties_multiple_actions_and_stale_evidence(self):
        for code in ['import os\ndef run(browser):\n browser.click("c1","hash")',
                     'def run(browser):\n __import__("os").system("id")',
                     'def run(browser):\n browser.__class__("hash")',
                     'def run(browser):\n browser.click("c1","old")',
                     'def run(browser):\n browser.click("c1","hash")\n browser.click("c2","hash")',
                     'def run(browser):\n browser.click(candidate="c1",evidence="hash")',
                     'def run(browser):\n browser.click(str("c1"),"hash")',
                     'def run(browser):\n return browser.click("c1","hash")',
                     'def run(browser):\n browser.type("password","hash")']:
            with self.subTest(code=code),self.assertRaises(ValueError):parse_function(code,'hash')

    def test_code_cannot_click_unobserved_or_dangerous_controls(self):
        for candidate in [{'id':'c1','kind':'heading','label':'News'},{'id':'c1','kind':'control','label':'Delete account'},{'id':'missing','kind':'control','label':'News'}]:
            with patch('triage.journey.complete',return_value=json.dumps({'python':'def run(browser):\n browser.click("c1","hash")','result':'clicked'})),self.assertRaises(ValueError):
                propose_step('Click News',{'evidence':'hash','candidates':[candidate]})

    def test_read_method_is_observation_only_not_an_invented_article_count(self):
        self.assertEqual(parse_function('def run(browser):\n browser.read_articles("hash")','hash')['action'],'read')

class GeneratedWorkerTests(unittest.TestCase):
    @patch('triage.public_browser.socket.getaddrinfo', return_value=[(2,1,6,'',('34.134.219.254',443))])
    @patch('triage.journey.grid_status', return_value={'ready':True})
    def test_ai_generated_click_and_read_code_drives_worker_and_returns_actual_article_text(self,*_):
        import os,tempfile
        from pathlib import Path
        from threading import Lock
        from triage.browser_loop import BrowserRuns
        from triage.journey import start_journey,OBSERVE_PUBLIC
        from test_journey import Driver
        class Articles(Driver):
            def execute_script(self,script,*args):
                value=super().execute_script(script,*args)
                if script==OBSERVE_PUBLIC:value['articles']=[{'title':'Public security report','url':'https://or9.ca/news/report','text':'An observed public security report excerpt, never a model-invented article.'}] if self.clicked else []
                return value
        driver=Articles()
        def coder(messages,**kwargs):
            user=json.loads(messages[-1]['content']);obs=user['observation'];method='click("c1", '+json.dumps(obs['evidence'])+')' if 'Click' in user['instruction'] else 'read_articles('+json.dumps(obs['evidence'])+')'
            return json.dumps({'python':'def run(browser):\n    browser.'+method,'result':'Invented model content, must not be used for read output'})
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'SELENIUM_GRID_URL':'http://grid:4444'}),patch('triage.journey.complete',side_effect=coder):
            manager=BrowserRuns(Path(directory),Lock(),lambda:'revision',driver_factory=lambda url:driver,evidence_kind='simulated')
            queued=start_journey(manager,'https://or9.ca/',['Click News','Read visible articles'])
            self.assertTrue(manager.generation_lock.acquire(timeout=5));manager.generation_lock.release()
            run=manager.read(queued['id']);self.assertEqual(run['status'],'passed',run)
            self.assertIn('browser.click(',run['steps'][1]['generatedPython']);self.assertIn('browser.read_articles(',run['steps'][2]['generatedPython'])
            self.assertEqual(run['steps'][2]['articles'][0]['title'],'Public security report')
            self.assertNotIn('Invented',run['steps'][2]['result']);self.assertEqual(driver.quits,1)

class InvalidEvidenceReadTests(unittest.TestCase):
    def test_stale_read_and_oversized_or_computed_source_is_rejected(self):
        for source in ['def run(browser):\n browser.read_articles("stale")','x'*4001,'def run(browser):\n browser.observe("h"+"ash")']:
            with self.subTest(source=source[:50]),self.assertRaises(ValueError):parse_function(source,'hash')

class GroundedSchemaTests(unittest.TestCase):
    def test_generation_schema_enumerates_only_safe_single_fresh_operations(self):
        observation={'evidence':'hash','articles':[],'candidates':[{'id':'c1','kind':'control','label':'News'},{'id':'c2','kind':'control','label':'Delete account'}]}
        source='def run(browser):\n    browser.click("c1", "hash")'
        with patch('triage.journey.complete',return_value=json.dumps({'python':source,'result':'candidate'})) as model:
            propose_step('Read visible articles',observation)
        allowed=model.call_args.kwargs['schema']['properties']['python']['enum']
        self.assertTrue(allowed);self.assertIn(source,allowed)
        self.assertFalse(any('read_articles' in code or 'observe(' in code or 'click("c2"' in code for code in allowed))
        for code in allowed:self.assertEqual(parse_function(code,'hash')['evidence'],'hash')
