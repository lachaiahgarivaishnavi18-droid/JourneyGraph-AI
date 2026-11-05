import React, { useState, useEffect } from 'react';
import { RefreshCw, Layers, Database } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, PieChart, Pie, Cell, Legend } from 'recharts';
import { api } from '../api';
export type Data = Record<string, any>;
export const palette = ['#13a88a', '#8274d6', '#e8ae54', '#538ec6', '#d47c87', '#8da783'];
export function useData(path: string, refresh = 0) {
    const [data, setData] = useState<any>(null), [error, setError] = useState(''), [loading, setLoading] = useState(true);
    useEffect(() => { if (!sessionStorage.getItem("jg-token")) {
        setLoading(false);
        return;
    } let active = true; setLoading(true); setError(''); api(path).then(d => { if (active)
        setData(d); }).catch(e => { if (active)
        setError(e.message); }).finally(() => { if (active)
        setLoading(false); }); return () => { active = false; }; }, [path, refresh]);
    return { data, error, loading };
}
export function Status({ error, loading }: {
    error?: string;
    loading?: boolean;
}) { return error ? <div role="alert" className="notice error">{error}</div> : loading ? <div role="status" className="loading"><RefreshCw size={18} className="spin"/> Retrieving stored evidence…</div> : null; }
export function Empty({ text = 'No matching data. Import a dataset or adjust your filters.' }: {
    text?: string;
}) { return <div className="empty"><Database size={28}/><p>{text}</p></div>; }
export function Panel({ title, subtitle, action, children, className = '' }: {
    title: string;
    subtitle?: string;
    action?: React.ReactNode;
    children: React.ReactNode;
    className?: string;
}) { return <section className={'panel ' + className}><div className="panel-head"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>{children}</section>; }
export function Tag({ children, tone = '' }: {
    children: React.ReactNode;
    tone?: string;
}) { return <span className={'tag ' + tone}>{children}</span>; }
export function DataTable({ rows, columns, onRow }: {
    rows: Data[];
    columns: {
        key: string;
        label: string;
        render?: (r: Data) => React.ReactNode;
    }[];
    onRow?: (r: Data) => void;
}) {
    const [page, setPage] = useState(1);
    useEffect(() => setPage(1), [rows]);
    const size = 12;
    if (!rows.length)
        return <Empty />;
    return <><div className="table-wrap"><table><thead><tr>{columns.map(c => <th key={c.key}>{c.label}</th>)}</tr></thead><tbody>{rows.slice((page - 1) * size, page * size).map((r, i) => <tr key={r.id || r.customer_id || i} className={onRow ? 'clickable' : ''} tabIndex={onRow ? 0 : undefined} onKeyDown={e => { if (onRow && (e.key === 'Enter' || e.key === ' ')) {
        e.preventDefault();
        onRow(r);
    } }} onClick={() => onRow?.(r)}>{columns.map(c => <td key={c.key}>{c.render ? c.render(r) : typeof r[c.key] === 'object' ? JSON.stringify(r[c.key]) : String(r[c.key] ?? '—')}</td>)}</tr>)}</tbody></table></div><div className="pagination"><span>{rows.length} records · page {page} of {Math.ceil(rows.length / size)}</span><button disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button><button disabled={page * size >= rows.length} onClick={() => setPage(page + 1)}>Next</button></div></>;
}
export function JsonDetails({ data, label = 'View structured evidence' }: {
    data: any;
    label?: string;
}) { return <details className="evidence"><summary>{label}</summary><pre>{JSON.stringify(data, null, 2)}</pre></details>; }
export function Trend({ data }: {
    data: Data[];
}) { return <div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data}><defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#13a88a" stopOpacity={.24}/><stop offset="100%" stopColor="#13a88a" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="var(--line)"/><XAxis dataKey="date" tickFormatter={v => v.slice(5)} minTickGap={45} tickLine={false} axisLine={false}/><YAxis tickLine={false} axisLine={false} width={35}/><Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 12 }}/><Area isAnimationActive={false} name="Interactions" type="monotone" dataKey="interactions" stroke="#13a88a" strokeWidth={2} fill="url(#area)"/><Area isAnimationActive={false} name="Purchases" type="monotone" dataKey="purchases" stroke="#8274d6" fill="transparent" strokeWidth={2}/></AreaChart></ResponsiveContainer></div>; }
export function Funnel({ data }: {
    data: Data[];
}) { const max = data[0]?.customers || 1; return <div className="funnel">{data.map((r, i) => <div className="funnel-row" key={r.stage}><div><span className="stage-index">0{i + 1}</span><span>{r.stage}</span><strong>{r.customers.toLocaleString()}</strong></div><div className="funnel-track"><div style={{ width: Math.max(r.customers / max * 100, 1) + '%', background: palette[i] }}/></div><small>{i ? `${r.dropoff}% drop from previous stage` : 'Ordered customer journey entry'}</small></div>)}</div>; }
export function SegmentChart({ data }: {
    data: Data[];
}) { return <div className="segment-chart"><ResponsiveContainer width="100%" height={220}><PieChart><Pie isAnimationActive={false} data={data} nameKey="name" dataKey="customers" innerRadius={60} outerRadius={85} paddingAngle={4} stroke="none">{data.map((_, i) => <Cell key={i} fill={palette[i % palette.length]}/>)}</Pie><Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 12 }}/><Legend iconType="circle" iconSize={8}/></PieChart></ResponsiveContainer></div>; }
export function Channels({ data }: {
    data: Data[];
}) { return <div className="channel-list">{data.map((c, i) => <div key={c.channel}><span className="channel-icon" style={{ color: palette[i % 6] }}><Layers size={18}/></span><div><b>{c.channel}</b><small>{c.customers} customers · {c.interactions} interactions</small></div><strong>{c.conversion_rate}%<small>conversion</small></strong></div>)}</div>; }
export function JourneyList({ data }: {
    data: Data[];
}) { const [limit, setLimit] = useState(30); return data.length ? <><div className="timeline">{data.slice(-limit).map(e => <div key={e.id}><span className="timeline-point"/><div><Tag tone={e.event_type === 'purchase' ? 'green' : ''}>{e.stage || e.event_type}</Tag><h3>{e.event_type.replaceAll('_', ' ')}<small>{e.entity_id}</small></h3><p>{e.channel} · {new Date(e.event_time).toLocaleString()} · {e.id}</p></div><span className="muted">#{e.sequence}</span></div>)}</div>{data.length > limit && <button onClick={() => setLimit(limit + 50)}>Show earlier events ({data.length - limit} remaining)</button>}</> : <Empty text="No events for this customer and filter selection."/>; }
