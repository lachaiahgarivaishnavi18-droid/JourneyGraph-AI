export async function api(path: string, options: RequestInit = {}) {
    const headers = new Headers(options.headers);
    const token = sessionStorage.getItem('jg-token');
    if (token)
        headers.set('Authorization', `Bearer ${token}`);
    if (options.body && !(options.body instanceof FormData))
        headers.set('Content-Type', 'application/json');
    const response = await fetch('/api' + path, { ...options, headers });
    if (!response.ok) {
        if (response.status === 401) {
            sessionStorage.removeItem('jg-token');
            window.dispatchEvent(new Event('jg-logout'));
        }
        const error = await response.json().catch(() => ({}));
        throw new Error(typeof error.detail === 'string' ? error.detail : `Request failed (${response.status}): check the supplied values`);
    }
    return response.json();
}
export const post = (path: string, body: unknown = {}) => api(path, { method: 'POST', body: JSON.stringify(body) });
export async function download(id: string, format: string) {
    const r = await fetch(`/api/reports/${id}/export?format=${format}`, { headers: { Authorization: 'Bearer ' + sessionStorage.getItem('jg-token') } });
    if (!r.ok)
        throw new Error('Export failed');
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement('a');
    a.href = url;
    a.download = `journeygraph-${id}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
}
