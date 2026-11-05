import { Network, Settings } from 'lucide-react';
import { api } from '../api';
import { useData, Status, Panel, Tag, DataTable, JsonDetails } from '../components/shared';
import type { Data } from '../components/shared';
export function AdminView({ page, refresh, notify, onChange }: {
    page: string;
    refresh: number;
    notify: (s: string) => void;
    onChange: () => void;
}) {
    const settings = useData('/settings', refresh), audit = useData(page === 'Audit Logs' ? '/audit' : '/settings', refresh);
    async function toggle(key: string, value: boolean) { try {
        await api('/settings/' + key, { method: 'PUT', body: JSON.stringify(key === 'llm' ? { enabled: value } : { include_predictions: value }) });
        onChange();
        notify('Configuration saved');
    }
    catch (e) {
        notify((e as Error).message);
    } }
    if (page === 'Audit Logs')
        return <Panel title="Audit trail" subtitle="Actions and identifiers only; passwords and API keys are excluded."><Status error={audit.error} loading={audit.loading}/>{Array.isArray(audit.data) && <DataTable rows={audit.data} columns={[{ key: 'created_at', label: 'Time', render: r => new Date(r.created_at).toLocaleString() }, { key: 'actor', label: 'Actor' }, { key: 'action', label: 'Action' }, { key: 'detail', label: 'Metadata' }]}/>}</Panel>;
    return <><Status error={settings.error} loading={settings.loading}/>{settings.data && <Panel title={page} subtitle="Server-side configuration and current data provenance">{page === 'Data Sources' ? <DataTable rows={Object.entries(settings.data.data_sources).map(([source, count]) => ({ source, count }))} columns={[{ key: 'source', label: 'Source' }, { key: 'count', label: 'Stored events' }]}/> : <><div className="settings-row"><div><h3>LLM provider</h3><p>{settings.data.llm.configured ? 'External provider configured' : 'Local evidence summary — no API key configured'}</p><small>Set LLM_API_KEY, LLM_MODEL and LLM_BASE_URL on the server.</small></div><Tag tone="green">{settings.data.llm.mode}</Tag></div>{page === 'LLM Configuration' && <label className="checkbox"><input type="checkbox" checked={settings.data.settings.llm?.enabled ?? true} onChange={e => toggle('llm', e.target.checked)}/>Enable configured external LLM provider</label>}<div className="settings-row"><div><h3>Temporal graph storage</h3><p>{settings.data.graph.storage}</p><small>Neo4j: {settings.data.graph.neo4j_configured ? 'configured' : 'not configured; local temporal queries available'}</small></div><Network size={28}/></div>{page === 'Agent Configuration' && <label className="checkbox"><input type="checkbox" checked={settings.data.settings.agents?.include_predictions ?? true} onChange={e => toggle('agents', e.target.checked)}/>Allow prediction agent in workflows</label>}{page === 'System Settings' && <UserRoles refresh={refresh} notify={notify} onChange={onChange}/>}<JsonDetails data={settings.data} label="Inspect runtime configuration"/></>}</Panel>}</>;
}
export function UserRoles({ refresh, notify, onChange }: {
    refresh: number;
    notify: (s: string) => void;
    onChange: () => void;
}) { const users = useData('/users', refresh); return <><h3>Workspace roles</h3><Status error={users.error} loading={users.loading}/>{users.data && <DataTable rows={users.data} columns={[{ key: 'email', label: 'User' }, { key: 'role', label: 'Role', render: r => <select aria-label={'Role for ' + r.email} value={r.role} onChange={async (e) => { try {
            await api('/users/' + r.id + '/role', { method: 'PUT', body: JSON.stringify({ role: e.target.value }) });
            onChange();
            notify('Role updated');
        }
        catch (e) {
            notify((e as Error).message);
        } }}>{['viewer', 'analyst', 'admin'].map(role => <option key={role}>{role}</option>)}</select> }]}/>}</>; }
