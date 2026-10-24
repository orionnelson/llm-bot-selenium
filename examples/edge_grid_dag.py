# Owner-approved Edge UI examples. Run selected tasks; this is not a DAG scheduler.
from triage.dag import DAG, Task

dag = DAG(name='Edge Grid browser tests', tasks=(
    Task(task_id='start', label='Start', action='start', kind='start', routes={'next': 'or9-home'}),
    Task(task_id='or9-home', label='or9.ca read-only homepage', action='application', depends_on=('start',),
         routes={'next': 'fixture-check'}, params={
             'target': 'https://or9.ca/',
             'prompt': 'Check the public homepage title and visible body. No clicks, model or capture.',
             'browser': {'mode': 'read-only-or9'},
         }),
    Task(task_id='fixture-check', label='Synthetic errors chart', action='application', depends_on=('or9-home',),
         routes={'next': 'end'}, params={
             'target': 'http://127.0.0.1:8080/',
             'prompt': 'Inspect the errors chart and verify Errors: 0 using approved read-only controls.',
             'browser': {'allowed_actions': ['show-errors', 'open-details', 'return-home'],
                         'expected': {'id': 'errors', 'text': 'Errors: 0'}, 'max_steps': 3},
         }),
    Task(task_id='end', label='End', action='end', kind='end', depends_on=('fixture-check',)),
))
dag.validate()
