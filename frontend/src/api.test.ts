import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api, post } from './api';
import { pages, slug } from './navigation';
describe('authenticated API', () => {
    beforeEach(() => { sessionStorage.clear(); vi.restoreAllMocks(); });
    it('sends bearer credentials and JSON data', async () => { sessionStorage.setItem('jg-token', 'secret'); const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 'C001' }) }); vi.stubGlobal('fetch', fetcher); await post('/customers', { id: 'C001' }); const [url, options] = fetcher.mock.calls[0]; expect(url).toBe('/api/customers'); expect(options.headers.get('Authorization')).toBe('Bearer secret'); expect(JSON.parse(options.body)).toEqual({ id: 'C001' }); });
    it('clears expired credentials and raises the server error', async () => { sessionStorage.setItem('jg-token', 'expired'); vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({ detail: 'Authentication required' }) })); await expect(api('/customers')).rejects.toThrow('Authentication required'); expect(sessionStorage.getItem('jg-token')).toBeNull(); });
    it('has all requested pages with unique routes', () => { expect(pages).toHaveLength(48); expect(new Set(pages.map(slug)).size).toBe(48); });
});
