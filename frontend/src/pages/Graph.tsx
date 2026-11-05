import { useState, useMemo } from 'react';
import { ArrowRight, RefreshCw, X } from 'lucide-react';
import { ReactFlow, Background, Controls, MiniMap, MarkerType } from '@xyflow/react';
import { api, post } from '../api';
import { useData, Status, Empty, Panel, Tag, DataTable, JsonDetails } from '../components/shared';
import type { Data } from '../components/shared';
export function GraphView({ page, refresh, notify }: {
    page: string;
    refresh: number;
    notify: (s: string) => void;
}) {
    const [id, setId] = useState('C001'), [at, setAt] = useState(''), [known, setKnown] = useState(''), [before, setBefore] = useState(''), [comparison, setComparison] = useState<Data | null>(null), [selected, setSelected] = useState<Data | null>(null);
    const params = new URLSearchParams();
    if (id)
        params.set('customer_id', id);
    if (at)
        params.set('at', new Date(at).toISOString());
    if (known)
        params.set('known_at', new Date(known).toISOString());
    const { data, error, loading } = useData('/graph/explore?' + params.toString(), refresh);
    const patterns = useData('/graph/patterns', refresh);
    const projection = useMemo(() => { if (!data)
        return { nodes: [], edges: [] }; const ns = data.nodes.slice(0, 80); const ids = new Set(ns.map((n: Data) => n.id)); const es = data.edges.filter((e: Data) => ids.has(e.source) && ids.has(e.target)).slice(-160); return { nodes: ns.map((n: Data, i: number) => ({ id: n.id, data: { label: n.label }, position: n.kind === 'customer' ? { x: 320, y: 220 } : { x: 320 + Math.cos(i * 2 * Math.PI / Math.max(ns.length - 1, 1)) * 280, y: 220 + Math.sin(i * 2 * Math.PI / Math.max(ns.length - 1, 1)) * 180 }, style: { background: n.kind === 'customer' ? '#13a88a' : n.kind === 'channel' ? '#eeeafc' : '#fff', color: n.kind === 'customer' ? 'white' : '#333b4e', border: '1px solid ' + (n.kind === 'customer' ? '#13a88a' : '#ddd8ef'), borderRadius: 12, width: 135, fontSize: 11, padding: 12 } })), edges: es.map((e: Data) => ({ id: e.id, source: e.source, target: e.target, label: e.relation.replace('CUSTOMER_', '').replaceAll('_', ' ').toLowerCase(), markerEnd: { type: MarkerType.ArrowClosed, color: '#a59ac9' }, style: { stroke: '#b4a7d1', strokeWidth: 1.3 }, labelStyle: { fontSize: 8, fill: '#7e728f' }, data: e })) }; }, [data]);
    async function compare() { try {
        if (!before || !at)
            throw new Error('Select both the before and valid-time dates');
        setComparison(await api('/graph/history?' + new URLSearchParams({ before: new Date(before).toISOString(), after: new Date(at).toISOString(), ...(known ? { known_at: new Date(known).toISOString() } : {}) })));
    }
    catch (e) {
        notify((e as Error).message);
    } }
    if (page === 'Graph Pattern Discovery')
        return <Panel title="Recurring temporal transitions" subtitle="Distinct customers with each consecutive event pair"><Status error={patterns.error} loading={patterns.loading}/>{patterns.data && <DataTable rows={patterns.data} columns={[{ key: 'path', label: 'Transition', render: r => r.path.join(' → ') }, { key: 'customers', label: 'Customers' }]}/>}</Panel>;
    return <><Panel title={page} subtitle="Stored temporal facts, projected into an interactive graph" action={<Tag tone="purple">Bitemporal query</Tag>}><form className="graph-filters" onSubmit={e => { e.preventDefault(); const values = new FormData(e.currentTarget); setAt(String(values.get("at") || "")); setKnown(String(values.get("known") || "")); }}><label>Customer (blank = all)<input value={id} onChange={e => setId(e.target.value)} placeholder="C001"/></label><label>Valid at (local time)<input type="datetime-local" name="at" defaultValue={at}/></label><label>Known at (local time)<input type="datetime-local" name="known" defaultValue={known}/></label><button className="primary" type="submit">Apply time filters</button><button type="button" onClick={async () => { try {
        const r = await post('/graph/build');
        notify(`Graph verified: ${r.relationships} stored relationships`);
    }
    catch (e) {
        notify((e as Error).message);
    } }} className="secondary"><RefreshCw size={15}/>Verify graph</button></form><Status error={error} loading={loading}/>{data && <><div className="graph-summary"><span><i className="dot"/>{data.nodes.length} entities</span><span>{data.edges.length} temporal facts</span><span>Click a node or relationship for evidence</span></div><div className="graph-canvas"><ReactFlow nodes={projection.nodes} edges={projection.edges} fitView nodesDraggable onNodeClick={(_, n) => setSelected(data.nodes.find((x: Data) => x.id === n.id))} onEdgeClick={(_, e) => setSelected(e.data || null)}><Background color="#d8d3e5" gap={24}/><Controls /><MiniMap maskColor="#eeeafc66" nodeColor="#8274d6"/></ReactFlow>{!data.nodes.length && <div className="graph-empty"><Empty text="No relationships match both time filters."/></div>}</div><p className="muted">{data.semantics} Display limited to 80 nodes / 160 edges; use a customer filter for detail.</p></>}{selected && <div className="selected-evidence"><div className="panel-head"><h3>Selected entity / relationship</h3><button className="icon-button" onClick={() => setSelected(null)} aria-label="Close details"><X size={16}/></button></div><pre>{JSON.stringify(selected, null, 2)}</pre></div>}</Panel>{page === 'Historical Graph Comparison' && <Panel title="Compare two historical graph states" subtitle="Comparison is global; the customer filter above applies to the explorer only."><div className="inline-form"><label>Before (local time)<input type="datetime-local" value={before} onChange={e => setBefore(e.target.value)}/></label><button className="primary" onClick={compare}>Compare to valid-at date<ArrowRight size={16}/></button></div>{comparison && <><div className="mini-metrics"><div><b>{comparison.added.length}</b>Added facts</div><div><b>{comparison.removed.length}</b>Expired facts</div><div><b>{comparison.unchanged}</b>Unchanged</div></div><JsonDetails data={comparison}/></>}</Panel>}</>;
}
