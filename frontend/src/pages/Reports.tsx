import { useState } from 'react';
import { FileBarChart, Download } from 'lucide-react';
import { api, post, download } from '../api';
import { useData, Status, Panel, DataTable, JsonDetails } from '../components/shared';
export function ReportsView({ page, refresh, notify, onChange }: {
    page: string;
    refresh: number;
    notify: (s: string) => void;
    onChange: () => void;
}) {
    const reports = useData('/reports', refresh), runs = useData('/agents/executions', refresh);
    const [busy, setBusy] = useState(false);
    async function generate() { setBusy(true); try {
        await post('/reports/generate', { title: page + ' — ' + new Date().toLocaleDateString(), kind: page === 'Customer Reports' ? 'customers' : page === 'Journey Reports' ? 'journeys' : 'analytics' });
        onChange();
        notify('Snapshot report generated');
    }
    catch (e) {
        notify((e as Error).message);
    }
    finally {
        setBusy(false);
    } }
    if (page === 'Agent Execution Reports')
        return <Panel title="Agent execution reports" subtitle="Recorded results from real workflow runs"><Status error={runs.error} loading={runs.loading}/>{runs.data && <DataTable rows={runs.data} columns={[{ key: 'id', label: 'Execution' }, { key: 'status', label: 'Status' }, { key: 'started_at', label: 'Started' }, { key: 'outputs', label: 'Agent results', render: r => <JsonDetails data={r.outputs}/> }]}/>}</Panel>;
    return <Panel title={page} subtitle="Generate an immutable analytics snapshot, then export JSON or CSV." action={<button className="primary" disabled={busy} onClick={generate}><FileBarChart size={16}/>{busy ? 'Generating…' : 'Generate report'}</button>}><Status error={reports.error} loading={reports.loading}/>{reports.data && <DataTable rows={reports.data} columns={[{ key: 'title', label: 'Report' }, { key: 'created_at', label: 'Generated', render: r => new Date(r.created_at).toLocaleString() }, { key: 'export', label: 'Download', render: r => <div className="button-row">{['json', 'csv'].map(format => <button key={format} className="secondary" onClick={() => download(r.id, format).catch(e => notify(e.message))}><Download size={14}/>{format.toUpperCase()}</button>)}</div> }]}/>}</Panel>;
}
