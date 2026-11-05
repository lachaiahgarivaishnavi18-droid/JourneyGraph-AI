import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { DataTable, Status, Empty } from './shared';
afterEach(cleanup);
describe('accessible data views', () => {
    it('paginates records and opens a customer with the keyboard', () => {
        const select = vi.fn();
        render(<DataTable rows={Array.from({ length: 15 }, (_, i) => ({ id: String(i), name: `Customer ${i}` }))} columns={[{ key: 'name', label: 'Name' }]} onRow={select}/>);
        expect(screen.getByText('Customer 0')).toBeVisible();
        expect(screen.queryByText('Customer 14')).toBeNull();
        fireEvent.click(screen.getByRole('button', { name: 'Next' }));
        expect(screen.getByText('Customer 14')).toBeVisible();
        fireEvent.keyDown(screen.getByText('Customer 14').closest('tr')!, { key: 'Enter' });
        expect(select).toHaveBeenCalledWith({ id: '14', name: 'Customer 14' });
    });
    it('shows an error and a helpful empty state', () => {
        render(<><Status error="API unavailable"/><Empty /></>);
        expect(screen.getByRole('alert')).toHaveTextContent('API unavailable');
        expect(screen.getByText(/Import a dataset/)).toBeVisible();
    });
});
