import { useState } from 'react';
import { Bot, Play, RefreshCw, CircleHelp } from 'lucide-react';
import { api, post } from '../api';
import { pages } from '../navigation';
import { useData, Status, Panel, Tag, DataTable, JsonDetails, palette } from '../components/shared';
import type { Data } from '../components/shared';
export function AgentView({ page, refresh, notify, onChange }: {
    page: string;
    refresh: number;
    notify: (s: string) => void;
    onChange: () => void;
}) {
    const { data, error, loading } = useData('/agents', refresh), runs = useData('/agents/executions', refresh);
    const [id, setId] = useState(''), [predictions, setPredictions] = useState(true), [busy, setBusy] = useState(false), [output, setOutput] = useState<Data | null>(null);
    const agentIndex = pages.indexOf(page) - pages.indexOf('Customer Profiling Agent');
    const focused = page === 'AI Agent Dashboard' ? null : data?.agents[agentIndex];
    async function run() { setBusy(true); try {
        const r = await post('/agents/run', { customer_id: id || null, include_predictions: predictions });
        setOutput(r);
        onChange();
        notify(r.status === 'completed' ? 'Agent workflow completed' : r.error || 'Workflow failed');
    }
    catch (e) {
        notify((e as Error).message);
    }
    finally {
        setBusy(false);
    } }
    return <><Panel title={focused?.name || 'Multi-agent workspace'} subtitle={focused?.description || 'A checkpointed LangGraph workflow. Every result is calculated from stored evidence.'} action={<Tag tone="purple">9 coordinated agents</Tag>}><div className="agent-run-bar"><label>Customer scope<input value={id} onChange={e => setId(e.target.value)} placeholder="All customers, or e.g. C001"/></label><label className="checkbox"><input type="checkbox" checked={predictions} onChange={e => setPredictions(e.target.checked)}/>Include evaluated predictions</label><button className="primary" disabled={busy} onClick={run}>{busy ? <RefreshCw className="spin" size={17}/> : <Play size={17}/>} {busy ? 'Analyzing stored journeys…' : 'Run analysis'}</button></div><Status error={error} loading={loading}/><div className="agent-grid">{data?.agents.map((a: Data, i: number) => <div key={a.id} className={'agent-card ' + (focused?.id === a.id ? 'focused' : '')}><div><span className="agent-icon" style={{ color: palette[i % 6], background: palette[i % 6] + '15' }}><Bot size={21}/></span><Tag tone={a.status === 'completed' ? 'green' : ''}>{a.status.replaceAll('_', ' ')}</Tag></div><small>AGENT {String(i + 1).padStart(2, '0')}</small><h3>{a.name}</h3><p>{a.description}</p></div>)}</div><div className="notice"><CircleHelp size={16}/>Recommendations are proposals for human review. This platform never contacts customers or applies interventions.</div></Panel>{(output || data?.latest_execution) && <Panel title="Execution evidence" subtitle={(output || data.latest_execution).id}><JsonDetails data={focused ? (output || data.latest_execution).outputs?.[focused.id] || { status: 'Not executed in this run' } : (output || data.latest_execution)} label="Inspect agent outputs"/></Panel>}<Panel title="Execution history" subtitle="Persisted run status, timestamps, and structured outputs"><Status error={runs.error} loading={runs.loading}/>{runs.data && <DataTable rows={runs.data} onRow={r => setOutput(r)} columns={[{ key: 'id', label: 'Execution ID', render: r => <code>{r.id.slice(0, 12)}</code> }, { key: 'customer_id', label: 'Customer', render: r => r.customer_id || 'All customers' }, { key: 'status', label: 'Status', render: r => <Tag tone={r.status === 'completed' ? 'green' : ''}>{r.status}</Tag> }, { key: 'started_at', label: 'Started', render: r => new Date(r.started_at).toLocaleString() }, { key: 'finished_at', label: 'Finished', render: r => r.finished_at ? new Date(r.finished_at).toLocaleString() : '—' }]}/>}</Panel></>;
}
