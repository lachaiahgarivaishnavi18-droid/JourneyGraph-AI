import { useState } from 'react';
import { Search, Upload } from 'lucide-react';
import { api } from '../api';
import { useData, Status, Panel, Tag, DataTable, JsonDetails } from '../components/shared';
import type { Data } from '../components/shared';
export function ImportView({ refresh, notify, onChange }: {
    refresh: number;
    notify: (s: string) => void;
    onChange: () => void;
}) {
    const [file, setFile] = useState<File | null>(null), [kind, setKind] = useState('events'), [mapping, setMapping] = useState('{}'), [result, setResult] = useState<Data | null>(null), [busy, setBusy] = useState(false), [previewed, setPreviewed] = useState(false);
    const [synthetic, setSynthetic] = useState(false);
    const history = useData('/imports', refresh);
    async function upload(preview: boolean) { if (!file)
        return; setBusy(true); try {
        JSON.parse(mapping);
        const body = new FormData();
        body.append('file', file);
        body.append('kind', kind);
        body.append('mapping', mapping);
        body.append('synthetic', String(synthetic));
        const r = await api('/imports' + (preview ? '/preview' : ''), { method: 'POST', body });
        setResult(r);
        setPreviewed(preview && !r.errors.length);
        if (!preview) {
            onChange();
            notify(r.status === 'completed' ? `${r.inserted} records imported` : 'File rejected; no data imported');
        }
    }
    catch (e) {
        notify((e as Error).message);
    }
    finally {
        setBusy(false);
    } }
    return <><Panel title="Bring your journey data together" subtitle="CSV or JSON · UTF-8 · up to 5 MB / 10,000 rows · import customers before events"><div className="import-layout"><div><label className="upload-zone"><Upload size={32}/><strong>{file ? file.name : 'Choose a customer or event dataset'}</strong><span>CSV or JSON from your computer</span><input aria-label="Select dataset" type="file" accept=".csv,.json" onChange={e => { setFile(e.target.files?.[0] || null); setResult(null); setPreviewed(false); }}/></label><div className="inline-form"><label>Dataset type<select value={kind} onChange={e => { setKind(e.target.value); setPreviewed(false); }}><option value="events">Customer events</option><option value="customers">Customers</option></select></label></div><label className="checkbox"><input type="checkbox" checked={synthetic} onChange={e=>{setSynthetic(e.target.checked);setPreviewed(false)}}/>This file contains synthetic demonstration data</label><label>Column mapping (source → target, JSON)<textarea value={mapping} onChange={e => { setMapping(e.target.value); setPreviewed(false); }} placeholder={'{"user_id":"customer_id"}'}/></label><div className="button-row"><button disabled={!file || busy} className="secondary" onClick={() => upload(true)}><Search size={16}/>Validate & preview</button><button disabled={!previewed || busy} className="primary" onClick={() => upload(false)}><Upload size={16}/>Import validated data</button></div></div><div className="import-guide"><Tag tone="green">IMPORT CONTRACT</Tag><h3>A reliable graph starts with reliable events.</h3><p>Each event needs a unique ID, existing customer ID, event type, channel, entity ID, and a timestamp with timezone.</p><code>event_id, customer_id, event_type,<br />entity_id, channel, event_time,<br />properties</code><p>Customer columns: <code>id, name, email, region</code>. Email and region are optional.</p><p>Duplicate IDs are skipped. Invalid rows reject the whole file. Missing event properties default to an empty object.</p></div></div>{busy && <Status loading/>}{result && <><div className="notice">{result.policy || result.status} · {result.rows} rows · {result.valid ?? result.inserted} valid / inserted · {result.duplicates} duplicates</div>{result.errors?.length > 0 && <DataTable rows={result.errors} columns={[{ key: 'row', label: 'Row' }, { key: 'message', label: 'Validation error' }]}/>}<JsonDetails data={result.preview || result} label="Dataset preview and validation result"/></>}</Panel><Panel title="Import history" subtitle="Stored validation outcome for each import attempt"><Status error={history.error} loading={history.loading}/>{history.data && <DataTable rows={history.data} columns={[{ key: 'filename', label: 'File' }, { key: 'created_at', label: 'Imported at', render: r => new Date(r.created_at).toLocaleString() }, { key: 'status', label: 'Status', render: r => <Tag tone={r.result.status === 'completed' ? 'green' : 'amber'}>{r.result.status}</Tag> }, { key: 'inserted', label: 'Inserted', render: r => r.result.inserted }, { key: 'duplicates', label: 'Duplicates', render: r => r.result.duplicates }]}/>}</Panel></>;
}
