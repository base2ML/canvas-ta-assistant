import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Settings from './Settings';
import { BrowserRouter } from 'react-router-dom';

describe('Settings', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        globalThis.fetch = vi.fn();
    });

    it('renders TA Dashboard section with toggle label', async () => {
        const mockSettingsResponse = {
            ok: true,
            json: async () => ({
                course_id: null, course_name: null, canvas_api_url: 'https://canvas.example.com',
                last_sync: null, test_mode: false, max_late_days_per_assignment: 3,
                sandbox_course_id: '', timezone: null, data_path: '/data',
                total_late_day_bank: 6, penalty_rate_per_day: 1, per_assignment_cap: 2,
                late_day_eligible_groups: [], ta_breakdown_mode: 'group'
            })
        };

        // Mock multiple fetch calls (settings, sync status, templates, etc.)
        globalThis.fetch.mockResolvedValue(mockSettingsResponse);

        render(
            <BrowserRouter>
                <Settings />
            </BrowserRouter>
        );

        await waitFor(() => {
            expect(screen.getByText('TA Dashboard')).toBeInTheDocument();
        });

        expect(screen.getByText('Use actual grader from Canvas (grader_id)')).toBeInTheDocument();
    });
});
