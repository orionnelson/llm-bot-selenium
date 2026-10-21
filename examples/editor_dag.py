# Author functionality here first. The UI renders this definition; layout is separate.
from triage.dag import DAG, Task

dag = DAG(name='DAG-first SRE check', tasks=(
    Task(task_id='start', label='Start', action='start', kind='start', routes={'next': 'check'}),
    Task(task_id='check', label='Review Lambda check', action='lambda', depends_on=('start',),
         routes={'next': 'end'}, params={'target': 'synthetic-example'}),
    Task(task_id='end', label='End', action='end', kind='end', depends_on=('check',)),
))
dag.validate()
