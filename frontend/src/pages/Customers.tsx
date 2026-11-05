import React, { useState } from 'react';
import { Search, RefreshCw, X } from 'lucide-react';
import { api, post } from '../api';
import { useData, Status, Panel, Tag, DataTable, JsonDetails, Channels, JourneyList } from '../components/shared';
export function CustomerView({ page, notify, refresh, onChange }: {
    page: string;
    notify: (s: string) => void;
    refresh: number;
    onChange: () => void;
}) {
    const [search, setSearch] = useState(''), [selected, setSelected] = useState(''), [showCreate, setShowCreate] = useState(false);
    const { data, error, loading } = useData('/customers?page_size=100&search=' + encodeURIComponent(search), refresh);
    const details = useData('/customers/' + (selected || 'C001'), refresh), timeline = useData('/journeys/' + (selected || 'C001'), refresh);
    const [form, setForm] = useState({ id: '', name: '', region: 'Unknown' });
    async function create(e: React.FormEvent) { e.preventDefault(); try {
        await post('/customers', form);
        setShowCreate(false);
        onChange();
        notify('Customer created');
    }
    catch (e) {
        notify((e as Error).message);
    } }
    if (page === 'Customer Segmentation')
        return <Panel title="RFM customer segments" subtitle="Inactive >30 days · Champions ≥5 purchases · Returning ≥2 · New buyers ≥1"><button className="secondary" onClick={async () => { try {
            await post('/segments/refresh');
            onChange();
            notify('Segments recalculated');
        }
        catch (e) {
            notify((e as Error).message);
        } }}><RefreshCw size={16}/>Recalculate segments</button><Status error={error} loading={loading}/>{data && <DataTable rows={data.items} columns={[{ key: 'id', label: 'Customer' }, { key: 'name', label: 'Name' }, { key: 'segment', label: 'Segment', render: r => <Tag tone="green">{r.segment}</Tag> }, { key: 'recency_days', label: 'Recency (days)' }, { key: 'frequency', label: 'Purchases' }, { key: 'monetary', label: 'Recorded value ($)' }]}/>}</Panel>;
    return <><Panel title={page === 'Customer Lifetime Value' ? 'Observed customer value' : page} subtitle={page === 'Customer Lifetime Value' ? 'Recorded purchase value; this is not a forecast of lifetime value.' : 'Select a customer to explore their stored journey.'} action={<button className="secondary" onClick={() => setShowCreate(true)}>Add customer</button>}><div className="search-field"><Search size={16}/><input aria-label="Search customers" placeholder="Search customer name or ID…" value={search} onChange={e => setSearch(e.target.value)}/></div><Status error={error} loading={loading}/>{data && <><DataTable rows={data.items} onRow={r => setSelected(r.id)} columns={[{ key: 'name', label: 'Customer', render: r => <div className="person"><span>{r.id.slice(-2)}</span><div><b>{r.name}</b><small>{r.id} · {r.region}</small></div></div> }, { key: 'segment', label: 'Segment', render: r => <Tag>{r.segment}</Tag> }, { key: 'touchpoints', label: 'Touchpoints' }, { key: 'frequency', label: 'Purchases' }, { key: 'monetary', label: 'Recorded value ($)' }, { key: 'recency_days', label: 'Recency (days)' }, { key: 'source', label: 'Provenance' }]}/>{data.total > 100 && <p className="muted">Showing first 100 of {data.total} customers. Narrow your search to find additional customers.</p>}</>}</Panel>{(selected || page === 'Customer Profile' || page === 'Customer Behavior Analysis') && details.data && <Panel title={details.data.name} subtitle={`${details.data.id} · ${details.data.segment} · ${details.data.source}`}><div className="mini-metrics"><div><b>{details.data.touchpoints}</b>Touchpoints</div><div><b>{details.data.channels}</b>Channels</div><div><b>${details.data.monetary}</b>Recorded purchases</div><div><b>{timeline.data?.duration_days ?? '—'}</b>Journey days</div></div><JourneyList data={timeline.data?.events || []}/><JsonDetails data={details.data}/></Panel>}{showCreate && <div className="modal-backdrop"><form className="modal" onSubmit={create}><div className="panel-head"><h2>Add customer</h2><button type="button" className="icon-button" onClick={() => setShowCreate(false)} aria-label="Close"><X /></button></div>{Object.keys(form).map(k => <label key={k}>{k}<input required value={form[k as keyof typeof form]} onChange={e => setForm({ ...form, [k]: e.target.value })}/></label>)}<button className="primary">Create customer</button></form></div>}</>;
}
