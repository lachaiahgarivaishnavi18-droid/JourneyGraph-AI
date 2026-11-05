import { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { api } from '../api';
import { useData, Status, Panel, DataTable, JsonDetails, Trend, Funnel, Channels, JourneyList } from '../components/shared';
import type { Data } from '../components/shared';
export function JourneyView({ page, data, query, refresh }: {
    page: string;
    data: Data;
    query: string;
    refresh: number;
}) {
    const [id, setId] = useState('C001'), [input, setInput] = useState('C001');
    const result = useData('/journeys/' + encodeURIComponent(id) + query, refresh);
    if (['Journey Explorer', 'Journey Timeline'].includes(page))
        return <Panel title="Reconstruct a customer journey" subtitle="Ordered by event time, with persisted timestamps and provenance"><form className="inline-form" onSubmit={e => { e.preventDefault(); setId(input); }}><label>Customer ID<input value={input} onChange={e => setInput(e.target.value)}/></label><button className="primary">Explore journey<ArrowRight size={16}/></button></form><Status error={result.error} loading={result.loading}/>{result.data && <><div className="mini-metrics"><div><b>{result.data.events.length}</b>Events</div><div><b>{result.data.channel_transitions}</b>Channel transitions</div><div><b>{result.data.duration_days}</b>Journey days</div></div><JourneyList data={result.data.events}/></>}</Panel>;
    if (page === 'Cross-Channel Analysis')
        return <Panel title="Cross-channel performance" subtitle="Descriptive conversion by event channel; not causal attribution"><Channels data={data.channels}/><DataTable rows={data.channels} columns={['channel', 'customers', 'interactions', 'conversions', 'conversion_rate'].map(k => ({ key: k, label: k.replaceAll('_', ' ') }))}/></Panel>;
    if (page === 'Cohort Analysis')
        return <Panel title="First-observed activity cohorts" subtitle="Grouped by first event in selected data; not account creation cohort"><DataTable rows={data.cohorts} columns={[{ key: 'month', label: 'First observed month' }, { key: 'customers', label: 'Customers' }, { key: 'converted', label: 'Purchased' }, { key: 'repeat', label: 'Repeat purchasers' }, { key: 'share', label: 'Purchase share', render: r => (r.converted / r.customers * 100).toFixed(1) + '%' }]}/></Panel>;
    if (page === 'Conversion Path Analysis')
        return <Panel title="Observed conversion paths" subtitle="First six events per customer in the current selection"><DataTable rows={data.paths} columns={[{ key: 'path', label: 'Path' }, { key: 'customers', label: 'Customers' }]}/></Panel>;
    return <div className="two-columns"><Panel title={page === 'Drop-off Analysis' ? 'Where journeys lose momentum' : 'Sequential conversion funnel'} subtitle={data.definitions.funnel}><Funnel data={data.funnel}/><div className="notice">Cart drop-off: {data.metrics.dropoff_rate}% — {data.definitions.dropoff_rate}</div></Panel><Panel title="Purchase activity" subtitle="Daily observed purchases"><Trend data={data.trend}/><JsonDetails data={data.definitions} label="Metric definitions"/></Panel></div>;
}
