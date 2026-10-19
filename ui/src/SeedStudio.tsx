import { useEffect, useRef, useState, type DragEvent, type FormEvent } from 'react';
import { Background, BackgroundVariant, Controls, Handle, MiniMap, Position, ReactFlow, useNodesState, useReactFlow, type Connection, type Node, type NodeProps } from '@xyflow/react';
import fixture from '../../shared/synthetic.workflow.json';
import { addParallel, createSeed, MAX_BYTES, parseWorkflow, portable, safeUrl, serialize, topological, uid, validate, type Workflow, type WorkflowNode } from './workflow';

const STORAGE = 'workflow-studio/v1/explicit-save';
type CardNode = Node<{ item: WorkflowNode }, 'workflow'>;
function Card({ data, selected }: NodeProps<CardNode>) {
  const n = data.item;
  return <article className={`node-card ${selected ? 'selected' : ''}`}>
    <Handle type="target" position={Position.Left} aria-label={`Input of ${n.title}`} />
    <div className="node-kind">{n.kind === 'fork' ? '⑂' : n.kind === 'join' ? '⑃' : n.kind === 'page' ? '◫' : '◇'} {n.kind}</div>
    <strong>{n.title}</strong>
    <span className={`badge ${n.provenance}`}>{n.provenance}</span>
    <small>{Object.keys(n.bindings).length ? Object.entries(n.bindings).map(([k, v]) => `${k} → {${v}}`).join(' · ') : 'No parameter bindings'}</small>
    <Handle type="source" position={Position.Right} aria-label={`Output of ${n.title}`} />
  </article>;
}
const nodeTypes = { workflow: Card };
const errorMessage = (e: unknown) => e instanceof Error ? e.message : 'Operation failed';

export default function App() {
  const [flow, setFlow] = useState<Workflow>(() => validate(structuredClone(fixture)));
  const [selectedId, select] = useState('enter');
  const [edgeId, selectEdge] = useState<string>();
  const [message, setMessage] = useState('Synthetic fixture loaded. No browser capture or model invocation has occurred.');
  const [error, setError] = useState('');
  const [seedUrl, setSeedUrl] = useState('https://example.com/search?query={xyz}');
  const [nodes, setNodes, onNodesChange] = useNodesState<CardNode>([]);
  const { screenToFlowPosition, fitView } = useReactFlow();
  const selected = flow.nodes.find(n => n.id === selectedId);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setNodes(flow.nodes.map(item => ({ id: item.id, type: 'workflow', position: item.position, data: { item }, selected: item.id === selectedId })));
  }, [flow, selectedId, setNodes]);

  function run(work: () => void) {
    try { work(); setError(''); } catch (e) { setError(errorMessage(e)); }
  }
  function commit(candidate: Workflow, notice = 'Workflow updated in memory.') {
    const valid = validate(candidate);
    setFlow(valid); setMessage(notice); setError('');
  }
  function replace(candidate: Workflow, notice: string) {
    commit(candidate, notice); select(candidate.nodes[0].id); selectEdge(undefined);
    requestAnimationFrame(() => { void fitView({ padding: 0.25 }); });
  }
  function updateNode(next: WorkflowNode) { run(() => commit({ ...flow, nodes: flow.nodes.map(n => n.id === next.id ? next : n) })); }
  function add(kind: 'action' | 'segment' | 'parallel', position = { x: 120, y: 400 }) {
    run(() => {
      if (kind === 'parallel') { commit(addParallel(flow, position), 'Paired fork/join group added. Connect its fork input and join output to build a larger flow.'); return; }
      const id = uid(kind);
      commit({ ...flow, nodes: [...flow.nodes, { id, kind, title: kind === 'segment' ? 'Reusable page segment' : 'New semantic action', position, provenance: 'approved', bindings: {} }] });
      select(id);
    });
  }
  function connect(connection: Connection) {
    run(() => commit({ ...flow, edges: [...flow.edges, { id: uid('edge'), source: connection.source, target: connection.target }] }, 'Connection validated.'));
  }
  function removeSelected() {
    run(() => {
      if (edgeId) {
        commit({ ...flow, edges: flow.edges.filter(e => e.id !== edgeId) }); selectEdge(undefined); return;
      }
      if (!selected) return;
      const removed = new Set([selected.id]);
      if (selected.kind === 'fork' || selected.kind === 'join') removed.add(selected.pairId!);
      commit({ ...flow, nodes: flow.nodes.filter(n => !removed.has(n.id)), edges: flow.edges.filter(e => !removed.has(e.source) && !removed.has(e.target)) });
      select('');
    });
  }
  async function importFile(file?: File) {
    if (!file) return;
    try {
      if (file.size > MAX_BYTES) throw new Error('Manifest exceeds 1 MB');
      const candidate = portable(parseWorkflow(await file.text()));
      replace(candidate, 'JSON validated and imported. Parameter values cleared for privacy; provenance labels are imported claims.');
    } catch (e) { setError(errorMessage(e)); }
  }
  function exportFile() {
    run(() => {
      const blob = new Blob([serialize(portable(flow))], { type: 'application/json' });
      const url = URL.createObjectURL(blob), link = document.createElement('a');
      link.href = url; link.download = 'workflow.json'; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setMessage('Exported versioned JSON. Parameter values and media URL are excluded.');
    });
  }
  function drop(event: DragEvent) {
    event.preventDefault();
    const kind = event.dataTransfer.getData('application/workflow-kind');
    if (['action', 'segment', 'parallel'].includes(kind)) add(kind as 'action' | 'segment' | 'parallel', screenToFlowPosition({ x: event.clientX, y: event.clientY }));
  }

  return <div className="studio">
    <header className="topbar">
      <div className="brand"><span className="brand-icon">⌘</span><div><h1>Workflow Studio <small>01 / LOCAL</small></h1><p>Browser intent, made reusable.</p></div></div>
      <nav aria-label="Workflow files">
        <button onClick={() => run(() => { localStorage.setItem(STORAGE, serialize(portable(flow))); setMessage('Saved explicitly on this device. Parameter values and media URL excluded.'); })}>Save locally</button>
        <button onClick={() => run(() => { const raw = localStorage.getItem(STORAGE); if (!raw) throw new Error('No saved workflow on this device'); replace(portable(parseWorkflow(raw)), 'Loaded validated local workflow. Re-enter public parameter values.'); })}>Load</button>
        <button onClick={() => run(() => { localStorage.removeItem(STORAGE); setMessage('Local saved workflow deleted.'); })}>Clear saved</button>
        <button onClick={() => fileInput.current?.click()}>Import JSON</button>
        <button className="primary" onClick={exportFile}>Export JSON ↗</button>
        <input ref={fileInput} hidden type="file" accept=".json,application/json" aria-label="Import workflow JSON" onChange={e => { void importFile(e.target.files?.[0]); e.target.value = ''; }} />
      </nav>
    </header>
    <div className="notice"><span className="live-dot" />{flow.synthetic ? 'SYNTHETIC FIXTURE' : 'OFFLINE MANIFEST'}<span>Local editing · no capture · no model connected · no execution engine</span></div>
    <div className="feedback"><p role="status">{message}</p>{error && <p role="alert" className="error">{error}</p>}</div>
    <div className="workspace">
      <aside className="palette panel" aria-label="Node palette">
        <h2>Building blocks</h2><p>Drag onto the canvas, or use Add with your keyboard.</p>
        {([['action', '◇', 'Semantic action', 'Click, inspect, navigate'], ['segment', '▤', 'Reusable segment', 'A named page region or step'], ['parallel', '⑂', 'Parallel group', 'Paired fork + branches + join']] as const).map(([kind, icon, title, subtitle]) =>
          <div className="palette-card" key={kind} draggable onDragStart={e => { e.dataTransfer.setData('application/workflow-kind', kind); e.dataTransfer.effectAllowed = 'move'; }}>
            <span>{icon}</span><strong>{title}</strong><small>{subtitle}</small><button aria-label={`Add ${title}`} onClick={() => add(kind)}>+ Add</button>
          </div>)}
        <h2>Page seed</h2>
        <form onSubmit={e => { e.preventDefault(); run(() => replace(createSeed(seedUrl), 'Created offline seed. Query values discarded; nothing was opened.')); }}>
          <label>Public URL / template<textarea value={seedUrl} onChange={e => setSeedUrl(e.target.value)} spellCheck={false} /></label>
          <button type="submit">Create seed</button>
        </form>
        <p className="hint">Literal query values become empty parameters. Sensitive query fields are redacted. Use public, non-sensitive examples only.</p>
        <button onClick={() => run(() => replace(validate(structuredClone(fixture)), 'Synthetic fixture reset. No recording is supplied.'))}>Reset synthetic fixture</button>
        <div className="legend"><h2>Provenance</h2>{(['observed', 'detected', 'model-proposed', 'approved', 'executed'] as const).map(p => <span key={p} className={`badge ${p}`}>{p}</span>)}<p>Labels describe manifest claims, not verified evidence. Fixture “observed” events are synthetic.</p></div>
      </aside>
      <main className="canvas-column">
        <div className="canvas-toolbar"><div><h2>{flow.title}</h2><span>{flow.nodes.length}/100 nodes · {flow.edges.length}/200 connections · DAG validated</span></div><button onClick={() => void fitView({ padding: 0.25 })}>Fit canvas</button><button onClick={removeSelected} disabled={!selected && !edgeId}>Delete {edgeId ? 'connection' : 'node'}</button></div>
        <div className="canvas" aria-label="Workflow graph canvas" onDrop={drop} onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }}>
          <ReactFlow<CardNode> nodes={nodes} edges={flow.edges.map(e => ({ ...e, selected: edgeId === e.id, animated: false }))} nodeTypes={nodeTypes}
            onNodesChange={changes => {
              onNodesChange(changes);
              const selection = changes.find(c => c.type === 'select' && c.selected);
              if (selection?.type === 'select') { select(selection.id); selectEdge(undefined); }
              const positions = new Map<string, { x: number; y: number }>();
              for (const c of changes) if (c.type === 'position' && c.position && !c.dragging) positions.set(c.id, c.position);
              if (positions.size) run(() => commit({ ...flow, nodes: flow.nodes.map(item => positions.has(item.id) ? { ...item, position: positions.get(item.id)! } : item) }));
            }} onNodeDragStop={(_, n) => run(() => commit({ ...flow, nodes: flow.nodes.map(item => item.id === n.id ? { ...item, position: n.position } : item) }))}
            onNodeClick={(_, n) => { select(n.id); selectEdge(undefined); }} onEdgeClick={(_, e) => { selectEdge(e.id); select(''); }}
            onConnect={connect} fitView fitViewOptions={{ padding: 0.25 }} minZoom={0.15} maxZoom={2} deleteKeyCode={null} colorMode="dark" nodesConnectable
            onPaneClick={() => selectEdge(undefined)} aria-label="Workflow graph; use Tab to focus nodes, Enter to select, arrows to move">
            <Background variant={BackgroundVariant.Dots} gap={22} size={1.2} color="#284342" /><MiniMap pannable zoomable nodeColor="#397c77" /><Controls showInteractive={false} />
          </ReactFlow>
        </div>
        <section className="timeline panel" aria-label="Action timeline">
          <div className="section-heading"><h2>Action timeline</h2><span>Topological order · parallel branches are not timestamps</span></div>
          <div className="timeline-items">{topological(flow).map((n, i) => <button key={n.id} className={n.id === selectedId ? 'active' : ''} aria-pressed={n.id === selectedId} onClick={() => { select(n.id); selectEdge(undefined); }}><span>{String(i + 1).padStart(2, '0')} · {n.timestamp === undefined ? 'no time' : `${n.timestamp}s`}</span><strong>{n.title}</strong><small>{n.provenance}</small></button>)}</div>
        </section>
        <Playback node={selected} report={setError} />
      </main>
      <aside className="inspector panel" aria-label="Workflow inspector">
        <PageParameters key={JSON.stringify(flow.page)} flow={flow} save={page => run(() => commit({ ...flow, page }))} />
        {selected ? <NodeInspector key={`${selected.id}:${JSON.stringify(selected)}`} node={selected} parameters={Object.keys(flow.page.parameters)} save={updateNode} duplicate={() => run(() => {
          if (selected.kind === 'fork' || selected.kind === 'join') throw new Error('Add a parallel group to duplicate fork/join structure.');
          const copy = { ...structuredClone(selected), id: uid(selected.kind), title: `${selected.title} copy`, position: { x: selected.position.x, y: selected.position.y + 180 } };
          commit({ ...flow, nodes: [...flow.nodes, copy] }); select(copy.id);
        })} /> : <p>Select a node or a timeline item to inspect its intent and parameters.</p>}
      </aside>
    </div>
    <footer>WORKFLOW STUDIO / v1 <span>Explicit save only · parameter values are session-only · media URL never saved</span></footer>
  </div>;
}

function PageParameters({ flow, save }: { flow: Workflow; save: (page: Workflow['page']) => void }) {
  const [urlTemplate, setTemplate] = useState(flow.page.urlTemplate);
  const [parameters, setParameters] = useState(flow.page.parameters);
  const [newName, setNewName] = useState('');
  return <section><h2>Page parameters</h2><p className="hint">Detected placeholders become shared bindings. Values stay in memory and are cleared on import/export/save.</p>
    <form onSubmit={e => { e.preventDefault(); save({ urlTemplate, parameters }); }}>
      <label>URL template<textarea value={urlTemplate} onChange={e => setTemplate(e.target.value)} spellCheck={false} /></label>
      {Object.entries(parameters).map(([name, value]) => <label key={name}>{`{${name}}`}<input value={value} maxLength={500} autoComplete="off" onChange={e => setParameters({ ...parameters, [name]: e.target.value })} /></label>)}
      <label>New public parameter name<input value={newName} onChange={e => setNewName(e.target.value)} placeholder="region" autoComplete="off" /></label>
      <button type="button" onClick={() => { if (newName && !['__proto__', 'constructor', 'prototype'].includes(newName)) { setParameters({ ...parameters, [newName]: '' }); setNewName(''); } }}>Add parameter draft</button>
      <button type="submit" className="primary">Apply page parameters</button>
    </form>
  </section>;
}

function NodeInspector({ node, parameters, save, duplicate }: { node: WorkflowNode; parameters: string[]; save: (n: WorkflowNode) => void; duplicate: () => void }) {
  const [draft, setDraft] = useState(structuredClone(node));
  const [prompt, setPrompt] = useState(node.prompt ?? 'Look for and click Enter');
  const [verb, setVerb] = useState<NonNullable<WorkflowNode['action']>['verb']>(node.action?.verb ?? 'click');
  const [target, setTarget] = useState(node.action?.target ?? 'Enter');
  const [bindingName, setBindingName] = useState('query');
  const [bindingParameter, setBindingParameter] = useState(parameters[0] ?? '');
  function propose(e: FormEvent) {
    e.preventDefault();
    save({ ...draft, prompt, action: { verb, target }, provenance: 'model-proposed', origin: 'user-authored', review: 'pending', title: `${verb}: ${target}`.slice(0, 160) });
  }
  return <>
    <section><div className="section-heading"><h2>Selected node</h2><span>{node.kind}</span></div>
      <code>{node.id}</code><p><span className={`badge ${node.provenance}`}>{node.provenance}</span></p>
      <form onSubmit={e => { e.preventDefault(); save(draft); }}>
        <label>Node title<input value={draft.title} maxLength={160} onChange={e => setDraft({ ...draft, title: e.target.value })} /></label>
        <label>Recording timestamp (seconds)<input type="number" min={0} max={86400} step="0.1" value={draft.timestamp ?? ''} onChange={e => { const next = { ...draft }; if (!e.target.value) delete next.timestamp; else next.timestamp = Number(e.target.value); setDraft(next); }} /></label>
        <h3>Shared parameter bindings</h3>
        {Object.entries(draft.bindings).map(([key, value]) => <div className="binding" key={key}><code>{key} → {`{${value}}`}</code><button type="button" aria-label={`Remove ${key} binding`} onClick={() => { const bindings = { ...draft.bindings }; delete bindings[key]; setDraft({ ...draft, bindings }); }}>×</button></div>)}
        <label>Binding name<input value={bindingName} onChange={e => setBindingName(e.target.value)} /></label>
        <label>Shared page parameter<select value={bindingParameter} onChange={e => setBindingParameter(e.target.value)}><option value="">Choose parameter</option>{parameters.map(p => <option key={p}>{p}</option>)}</select></label>
        <button type="button" disabled={!bindingName || !bindingParameter} onClick={() => setDraft({ ...draft, bindings: { ...draft.bindings, [bindingName]: bindingParameter } })}>Bind draft</button>
        <button className="primary" type="submit">Apply node changes</button>
      </form><button onClick={duplicate}>Duplicate reusable node</button>
    </section>
    {['action', 'segment'].includes(node.kind) && <section><h2>Prompt → proposal</h2><p className="hint">Offline candidate editor. No LLM request is made. “Model-proposed” is the IR review lane; this editor records origin: user-authored.</p>
      <form onSubmit={propose}>
        <label>Intent / prompt<textarea value={prompt} onChange={e => setPrompt(e.target.value)} maxLength={2000} /></label>
        <label>Candidate semantic verb<select value={verb} onChange={e => setVerb(e.target.value as typeof verb)}>{['click', 'inspect', 'navigate', 'type'].map(v => <option key={v}>{v}</option>)}</select></label>
        <label>Semantic target (public description)<input value={target} onChange={e => setTarget(e.target.value)} maxLength={500} /></label>
        <button type="submit">Stage pending candidate</button>
      </form>
      {node.action && <div className="proposal"><span>{node.review ?? 'Unreviewed'} · {node.origin ?? 'manifest claim'}</span><pre>{JSON.stringify(node.action, null, 2)}</pre><p>{node.prompt}</p></div>}
      {node.provenance === 'model-proposed' && <button className="primary" onClick={() => save({ ...node, provenance: 'approved', review: 'approved' })}>Approve intent only</button>}
      <button disabled title="Milestone 1 has no browser execution adapter">Execute unavailable</button><p className="hint">Approval changes review metadata only. Imported “executed” labels are not proof of execution.</p>
    </section>}
  </>;
}

function Playback({ node, report }: { node?: WorkflowNode; report: (s: string) => void }) {
  const [draft, setDraft] = useState('');
  const [media, setMedia] = useState('');
  const [ready, setReady] = useState(false);
  const [status, setStatus] = useState('No recording supplied.');
  const video = useRef<HTMLVideoElement>(null);
  function seek() {
    const el = video.current;
    if (!el || !ready) return;
    el.pause();
    if (node?.timestamp === undefined) { setStatus('Selected node has no recording timestamp. Native playback controls are available.'); return; }
    if (!Number.isFinite(el.duration) || node.timestamp > el.duration) { setStatus('Selected timestamp is outside the supplied recording.'); return; }
    el.currentTime = node.timestamp; setStatus(`Paused at ${node.timestamp}s for ${node.title}.`);
  }
  useEffect(seek, [node?.id, node?.timestamp, ready]);
  return <section className="playback panel" aria-label="Selected action recording inspector">
    <div className="section-heading"><h2>Session inspector</h2><span>{node?.title ?? 'Select an action'} · {node?.timestamp === undefined ? 'no timestamp' : `${node.timestamp}s`}</span></div>
    <div className="playback-content">
      <div className="media-slot">{media ? <video ref={video} src={media} controls preload="metadata" onLoadedMetadata={() => { setReady(true); setStatus('Actual supplied media loaded.'); }} onError={() => { setReady(false); setStatus('Unable to load supplied recording. Check its URL, format, and server permissions.'); }} /> : <div className="no-recording"><span>▷</span><strong>No recording supplied</strong><p>The synthetic fixture includes action timestamps, not video.</p></div>}</div>
      <div><p className="hint">Supply a public HTTP(S) media URL to load actual video. This contacts that media host only when you load it. It stays in memory and is never exported or saved.</p>
        <form onSubmit={e => { e.preventDefault(); try { const url = safeUrl(draft); setReady(false); setMedia(url); setStatus('Loading supplied media…'); report(''); } catch (e) { report(errorMessage(e)); } }}>
          <label>Optional actual media URL<input type="url" value={draft} onChange={e => setDraft(e.target.value)} placeholder="https://example.com/recording.webm" autoComplete="off" /></label>
          <button type="submit">Load supplied video</button><button type="button" onClick={() => { setMedia(''); setDraft(''); setReady(false); setStatus('No recording supplied.'); }}>Clear media</button>
        </form>
        <button disabled={!ready || node?.timestamp === undefined} onClick={seek}>Seek to selected action</button><p role="status">{status}</p>
      </div>
    </div>
  </section>;
}
