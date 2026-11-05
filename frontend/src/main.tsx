import React, { useState, useEffect, useCallback } from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Users, Route, Network, Bot, Sparkles, FileBarChart, Settings, ChevronDown, ArrowUpRight, ArrowRight, Search, Sun, Moon, LogOut, Upload, Download, RefreshCw, X, Check, Activity, Menu, ChevronRight, Database, Filter } from 'lucide-react';
import '@xyflow/react/dist/style.css';
import { api } from './api';
import { groups, pages, slug } from './navigation';
import './styles.css';
type Data = Record<string, any>;
const palette = ['#13a88a', '#8274d6', '#e8ae54', '#538ec6', '#d47c87', '#8da783'];
const iconMap: Record<string, React.ElementType> = { dashboard: LayoutDashboard, customers: Users, journey: Route, graph: Network, agents: Bot, insights: Sparkles, reports: FileBarChart, settings: Settings };
import { useData, Status, Panel, Tag, DataTable, JsonDetails, Trend, Funnel } from './components/shared';
import { Login } from './pages/Login';
import { Dashboard, RecentActivities } from './pages/Dashboard';
import { CustomerView } from './pages/Customers';
import { JourneyView } from './pages/Journeys';
import { GraphView } from './pages/Graph';
import { AgentView } from './pages/Agents';
import { InsightsView } from './pages/Insights';
import { ImportView } from './pages/Import';
import { ReportsView } from './pages/Reports';
import { AdminView } from './pages/Administration';
function App() {
    const [user, setUser] = useState<Data | null>(null), [checking, setChecking] = useState(true), [dark, setDark] = useState(localStorage.getItem('jg-theme') === 'dark'), [mobile, setMobile] = useState(false), [refresh, setRefresh] = useState(0), [toast, setToast] = useState(''), [search, setSearch] = useState('');
    const location = useLocation(), navigate = useNavigate();
    const page = pages.find(p => '/' + slug(p) === location.pathname) || 'Dashboard';
    const group = groups.find(g => g.pages.includes(page))!;
    const [start, setStart] = useState(''), [end, setEnd] = useState(''), [channel, setChannel] = useState(''), [segment, setSegment] = useState(''), [product, setProduct] = useState(''), [eventType, setEventType] = useState(''), [stage, setStage] = useState(''), [showFilters, setShowFilters] = useState(false);
    const params = new URLSearchParams();
    if (start)
        params.set('start', start + 'T00:00:00Z');
    if (end)
        params.set('end', end + 'T23:59:59.999999Z');
    if (channel)
        params.set('channel', channel);
    if (segment)
        params.set('segment', segment);
    if (product)
        params.set('product', product);
    if (eventType)
        params.set('event_type', eventType);
    if (stage)
        params.set('stage', stage);
    const query = '?' + params.toString();
    const overview = useData('/analytics/overview' + query, refresh);
    const notify = useCallback((s: string) => { setToast(s); }, []);
    useEffect(() => { if (!toast)
        return; const timer = setTimeout(() => setToast(''), 6000); return () => clearTimeout(timer); }, [toast]);
    useEffect(() => { if (sessionStorage.getItem('jg-token'))
        api('/auth/me').then(setUser).catch(() => setUser(null)).finally(() => setChecking(false));
    else
        setChecking(false); const logout = () => setUser(null); window.addEventListener('jg-logout', logout); return () => window.removeEventListener('jg-logout', logout); }, []);
    useEffect(() => { document.documentElement.dataset.theme = dark ? 'dark' : 'light'; localStorage.setItem('jg-theme', dark ? 'dark' : 'light'); }, [dark]);
    const go = (p: string) => { navigate('/' + slug(p)); setMobile(false); setSearch(''); };
    const changed = () => setRefresh(r => r + 1);
    if (checking)
        return <div className="app-loading"><Status loading/></div>;
    if (!user)
        return <Login onLogin={u => { setUser(u); changed(); }}/>;
    const overviewPage = group.name === 'Overview';
    const graphPage = group.name === 'Temporal Knowledge Graph';
    const journeyPage = group.name === 'Journey Analytics';
    const globalFilters = overviewPage || journeyPage;
    return <div className="app-shell"><aside className={mobile ? 'sidebar open' : 'sidebar'}><button className="brand" onClick={() => go('Dashboard')}><div className="brand-icon"><Network size={23}/></div>JourneyGraph <b>AI</b></button><div className="workspace-badge"><span className="workspace-avatar">JG</span><div><b>Research workspace</b><small>Customer intelligence</small></div><ChevronDown size={14}/></div><span className="nav-label">WORKSPACE</span><nav>{groups.map(g => { const Icon = iconMap[g.icon], active = g === group; return <div key={g.name} className="nav-group"><button className={'nav-parent ' + (active ? 'active' : '')} onClick={() => go(g.pages[0])}><Icon size={18}/><span>{g.name}</span>{active ? <ChevronDown size={14}/> : <ChevronRight size={14}/>}</button>{active && <div className="subnav">{g.pages.map(p => <NavLink key={p} className={p === page ? 'selected' : ''} to={'/' + slug(p)} onClick={() => setMobile(false)}>{p}</NavLink>)}</div>}</div>; })}</nav><div className="sidebar-bottom"><div><span className="dot"/>Local research environment</div><button onClick={() => go('Data Sources')}><Database size={15}/>Data provenance<ArrowUpRight size={14}/></button></div><div className="sidebar-user"><span className="avatar">{user.email.slice(0, 2).toUpperCase()}</span><div><b>{user.role === 'admin' ? 'Administrator' : user.role}</b><small>{user.email}</small></div><button className="icon-button" aria-label="Sign out" onClick={() => { sessionStorage.removeItem('jg-token'); setUser(null); }}><LogOut size={17}/></button></div></aside>{mobile && <div className="sidebar-overlay" onClick={() => setMobile(false)}/>}
  <div className="main-shell"><header className="topbar"><button aria-label="Open navigation" className="icon-button mobile-toggle" onClick={() => setMobile(!mobile)}><Menu /></button><div className="breadcrumb"><span>Workspace</span><ChevronRight size={13}/><b>{group.name}</b></div><div className="topbar-right"><div className="global-search"><Search size={16}/><input aria-label="Find a page" placeholder="Search workspace…" value={search} onChange={e => setSearch(e.target.value)}/><kbd>⌕</kbd>{search && <div className="search-results">{pages.filter(p => p.toLowerCase().includes(search.toLowerCase())).slice(0, 9).map(p => <button key={p} onClick={() => go(p)}>{p}<ArrowUpRight size={14}/></button>)}</div>}</div><button className="icon-button" aria-label="Toggle theme" onClick={() => setDark(!dark)}>{dark ? <Sun size={19}/> : <Moon size={19}/>}</button><button className="icon-button" aria-label="Refresh evidence" onClick={() => { changed(); notify('Refreshing stored evidence'); }}><RefreshCw size={18}/></button><span className="avatar small">{user.email.slice(0, 2).toUpperCase()}</span></div></header>
  <main><div className="page-heading"><div><div className="eyebrow">{group.name.toUpperCase()}</div><h1>{page}<span className="title-dot">.</span></h1><p>{overviewPage ? 'Your customer journeys, connected and understood.' : graphPage ? 'Explore how customer relationships evolve across time.' : 'Turn customer interactions into traceable intelligence.'}</p></div><div className="button-row">{globalFilters && <button className="secondary" onClick={() => setShowFilters(!showFilters)}><Filter size={15}/>Filters{params.size > 0 && <Tag>{params.size}</Tag>}</button>}<button className="secondary" onClick={() => go('Export Center')}><Download size={16}/>Export</button><button className="primary" onClick={() => go('Data Import')}><Upload size={16}/>Import data</button></div></div>
  {globalFilters && showFilters && <div className="filter-bar"><label>From (UTC)<input type="date" value={start} onChange={e => setStart(e.target.value)}/></label><label>To (UTC)<input type="date" value={end} onChange={e => setEnd(e.target.value)}/></label><label>Channel<select value={channel} onChange={e => setChannel(e.target.value)}><option value="">All channels</option>{['website', 'mobile', 'email', 'ads', 'support', 'social'].map(c => <option key={c}>{c}</option>)}</select></label><label>Segment<select value={segment} onChange={e => setSegment(e.target.value)}><option value="">All segments</option>{['Champions', 'Returning', 'New buyers', 'Explorers', 'Inactive'].map(s => <option key={s}>{s}</option>)}</select></label><label>Product ID<input value={product} onChange={e => setProduct(e.target.value)} placeholder="All products"/></label><label>Event<select value={eventType} onChange={e => setEventType(e.target.value)}><option value="">All events</option>{['website_visit', 'product_view', 'search', 'add_to_cart', 'purchase', 'email_open', 'ad_click', 'app_open', 'support', 'return', 'review'].map(s => <option key={s}>{s}</option>)}</select></label><label>Stage<select value={stage} onChange={e => setStage(e.target.value)}><option value="">All stages</option>{['Awareness', 'Acquisition', 'Consideration', 'Conversion', 'Retention', 'Advocacy'].map(s => <option key={s}>{s}</option>)}</select></label><button className="text-button" onClick={() => { setStart(''); setEnd(''); setChannel(''); setSegment(''); setProduct(''); setEventType(''); setStage(''); }}>Clear</button></div>}
  {overview.data && Object.keys(overview.data.sources).includes('synthetic-demo') && <div className="demo-banner"><span className="dot"/><b>Synthetic demonstration data</b><span>For research and testing · {overview.data.metrics.total_interactions.toLocaleString()} matching stored events</span><button onClick={() => go('Data Sources')}>View sources<ArrowRight size={13}/></button></div>}
  {(overviewPage || journeyPage) && <Status error={overview.error} loading={overview.loading}/>}
  {overviewPage && overview.data && (page === 'Dashboard' ? <Dashboard key={refresh} data={overview.data} navigate={go}/> : page === 'Customer Journey Overview' ? <><div className="two-columns"><Panel title="Journey progression" subtitle={overview.data.definitions.funnel}><Funnel data={overview.data.funnel}/></Panel><Panel title="Activity trend"><Trend data={overview.data.trend}/></Panel></div><Panel title="Customer activity heatmap" subtitle="UTC hour and weekday"><div className="heatmap">{['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, d) => <div key={day}><span>{day}</span>{Array.from({ length: 24 }, (_, h) => { const count = overview.data.heatmap.find((r: Data) => r.day === d && r.hour === h)?.events || 0; return <i key={h} title={`${day} ${h}:00 UTC — ${count} events`} style={{ background: `rgba(19,168,138,${Math.min(.95, .05 + count / 100)})` }}/>; })}</div>)}</div></Panel></> : page === 'Business KPIs' ? <Panel title="Calculated business metrics" subtitle="Definitions and denominators are part of each analysis"><DataTable rows={Object.entries(overview.data.metrics).map(([metric, value]) => ({ metric: metric.replaceAll('_', ' '), value }))} columns={[{ key: 'metric', label: 'Metric' }, { key: 'value', label: 'Value' }]}/><JsonDetails data={overview.data.definitions} label="Definitions and measurement limits"/></Panel> : <RecentActivities query={query} refresh={refresh}/>)}
  {group.name === 'Customer Management' && <CustomerView page={page} notify={notify} refresh={refresh} onChange={changed}/>}
  {journeyPage && overview.data && <JourneyView page={page} data={overview.data} query={query} refresh={refresh}/>}
  {graphPage && <GraphView page={page} refresh={refresh} notify={notify}/>}
  {group.name === 'Multi-Agent Intelligence' && <AgentView page={page} refresh={refresh} notify={notify} onChange={changed}/>}
  {group.name === 'AI Insights' && <InsightsView page={page} notify={notify}/>}
  {group.name === 'Reports' && <ReportsView page={page} refresh={refresh} notify={notify} onChange={changed}/>}
  {group.name === 'Administration' && (page === 'Data Import' ? <ImportView refresh={refresh} notify={notify} onChange={changed}/> : <AdminView page={page} refresh={refresh} notify={notify} onChange={changed}/>)}
  <footer><span>JourneyGraph AI <span className="muted">/</span> Evidence before insight.</span><span>Temporal intelligence · Research edition</span></footer></main></div>{toast && <div className="toast" role="status"><Check size={17}/>{toast}<button className="icon-button" aria-label="Dismiss notification" onClick={() => setToast('')}><X size={15}/></button></div>}</div>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><HashRouter><App /></HashRouter></React.StrictMode>);
