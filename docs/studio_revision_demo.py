"""PYTHONPATH=.:tests python docs/studio_revision_demo.py
Actual temporary HTTP backend; synthetic DAG/model double, no model/browser run.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from test_dag_server import backend, request, commit
from test_test_integrations import saved, SOURCE
from triage.test_codegen import MODEL

with backend(saved(), test_mode=True) as (port, path, _):
    original = request(port)[1]
    changed = replace(saved(), tasks=(replace(saved().tasks[0],
        predicate={**saved().tasks[0].predicate, 'threshold': 9}), *saved().tasks[1:]))
    current = commit(port, original['revision'], changed.to_spec())[1]
    before = path.read_bytes()
    body = json.dumps({'nodeId': 'saved', 'instructions': 'Synthetic comparison'})
    candidate = {'source': SOURCE, 'model': MODEL, 'review': 'pending', 'executed': False}
    results = []
    with patch('triage.test_codegen.generate', return_value=candidate) as model:
        for label, revision in [('missing', None), ('stale', original['revision']),
                                ('wildcard', '*'), ('malformed', 'bad')]:
            headers = {'Content-Type': 'application/json'}
            if revision is not None:
                headers['If-Match'] = revision
            status, value = request(port, 'POST', body, headers, '/api/python/generate')
            assert status == 409 and 'source' not in value
            results.append({'clientRevision': label, 'status': status, 'candidateReturned': False})
        model.assert_not_called()
        status, value = request(port, 'POST', body, {'Content-Type': 'application/json',
            'If-Match': current['revision']}, '/api/python/generate')
        assert status == 200 and value == candidate
        assert model.call_args.args == (changed, 'saved', 'Synthetic comparison')
        assert model.call_count == 1 and path.read_bytes() == before
    root = Path(__file__).resolve().parents[1]
    print(json.dumps({'evidence': 'actual loopback HTTP; synthetic model double, not inference or browser',
        'beforeThreshold': 3, 'savedThreshold': 9, 'rejectedBeforeModel': results,
        'reloadedRevision': {'status': status, 'modelCalls': 1, 'modelTaskThreshold': 9,
                             'review': value['review'], 'executed': value['executed']},
        'canonicalSourceUnchangedByGeneration': path.read_bytes() == before,
        'sourceSHA256': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ['triage/dag_server.py', 'ui/src/App.tsx', 'ui/src/PythonInspector.tsx']}}, indent=2))
