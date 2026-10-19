/** Workflow Studio v1 IR. Structural schema: workflow.schema.json; semantic guards in both runtimes. */
export const VERSION = 'workflow-studio/v1' as const;
export type Kind = 'page' | 'action' | 'segment' | 'fork' | 'join';
export type Provenance = 'observed' | 'detected' | 'model-proposed' | 'approved' | 'executed';
export interface WorkflowNode {
  id: string;
  kind: Kind;
  title: string;
  position: { x: number; y: number };
  provenance: Provenance;
  bindings: Record<string, string>;
  pairId?: string;
  prompt?: string;
  action?: { verb: 'click' | 'navigate' | 'inspect' | 'type'; target: string };
  review?: 'pending' | 'approved';
  origin?: 'offline-template' | 'user-authored' | 'model';
  timestamp?: number;
}
export interface Workflow {
  version: typeof VERSION;
  title: string;
  synthetic: boolean;
  page: { urlTemplate: string; parameters: Record<string, string> };
  nodes: WorkflowNode[];
  edges: { id: string; source: string; target: string }[];
}
