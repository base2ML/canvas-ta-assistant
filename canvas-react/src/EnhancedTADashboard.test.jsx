import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import EnhancedTADashboard from './EnhancedTADashboard';

// Mock child components to simplify testing
vi.mock('./components/SubmissionStatusCards', () => ({
    default: ({ metrics }) => <div data-testid="submission-cards">Submission Cards: {metrics.total_expected}</div>
}));

vi.mock('./components/AssignmentStatusBreakdown', () => ({
    default: (props) => (
        <div data-testid="assignment-breakdown">
            Breakdown: {props.assignmentStats?.length || 0} assignments
        </div>
    )
}));

describe('EnhancedTADashboard', () => {
    const mockBackendUrl = 'http://localhost:8000';
    const mockGetAuthHeaders = vi.fn().mockResolvedValue({ Authorization: 'Bearer token' });

    const mockCourses = {
        courses: [
            { id: '1', name: 'Course 1' },
            { id: '2', name: 'Course 2' }
        ]
    };

    const mockAssignments = {
        data_url: 'http://s3/assignments',
        assignments: [
            { id: 101, name: 'Assignment 1', due_at: '2023-01-01' }
        ]
    };

    const mockSubmissions = {
        data_url: 'http://s3/submissions',
        submissions: [
            { id: 1, user_id: 1, assignment_id: 101, workflow_state: 'graded' },
            { id: 2, user_id: 2, assignment_id: 101, workflow_state: 'submitted' }
        ]
    };

    const mockUsers = {
        data_url: 'http://s3/users',
        users: [
            { id: 1, name: 'Student 1' },
            { id: 2, name: 'Student 2' }
        ]
    };

    const mockGroups = {
        data_url: 'http://s3/groups',
        groups: [
            { name: 'TA Group A', members: [{ user_id: 1 }] }, // Object format
            { name: 'TA Group B', members: [2] }               // ID format (Regression test case)
        ]
    };

    const mockMetrics = {
        overall_metrics: { total_expected: 100 },
        by_assignment: [{ id: 101 }],
        by_ta: [
            { ta_name: 'TA Group A', student_count: 1, on_time: 0, late: 0, missing: 0 },
            { ta_name: 'TA Group B', student_count: 1, on_time: 0, late: 0, missing: 0 }
        ]
    };

    beforeEach(() => {
        vi.clearAllMocks();
        globalThis.fetch = vi.fn();
    });

    it('renders dashboard and shows provided courses', async () => {
        render(
            <EnhancedTADashboard
                backendUrl={mockBackendUrl}
                getAuthHeaders={mockGetAuthHeaders}
                courses={mockCourses.courses}
            />
        );

        expect(screen.getByText(/TA Grading Dashboard/i)).toBeInTheDocument();
        expect(screen.getByText('Course 1')).toBeInTheDocument();
    });

    it('loads course data and handles mixed group member formats', async () => {
        // 1. Load Course Data (4 API calls) - triggered by useEffect when courses prop is present
        globalThis.fetch
            .mockResolvedValueOnce({ ok: true, json: async () => ({ data_url: 'url-assignments' }) })
            .mockResolvedValueOnce({ ok: true, json: async () => ({ data_url: 'url-submissions' }) })
            .mockResolvedValueOnce({ ok: true, json: async () => ({ data_url: 'url-users' }) })
            .mockResolvedValueOnce({ ok: true, json: async () => ({ data_url: 'url-groups' }) });

        // 3. Load Metrics (happens before S3 data fetch because of useEffect timing)
        globalThis.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => mockMetrics
        });

        // 3b. Load Assignment Statistics (added by integration changes)
        globalThis.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => [] // Empty array for assignment stats
        });

        // 4. Load S3 Data (happens after initial 4 fetches resolve)
        const mockCombinedData = {
            assignments: mockAssignments.assignments,
            submissions: mockSubmissions.submissions,
            users: mockUsers.users,
            groups: mockGroups.groups
        };

        globalThis.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => mockCombinedData
        });

        render(
            <EnhancedTADashboard
                backendUrl={mockBackendUrl}
                getAuthHeaders={mockGetAuthHeaders}
                courses={mockCourses.courses}
            />
        );

        // Wait for data to load and TA table to appear
        await waitFor(() => {
            expect(screen.getByText('TA Workload Breakdown')).toBeInTheDocument();
        });

        // Verify TA Group A (Object format)
        expect(screen.getByText('TA Group A')).toBeInTheDocument();

        // Verify TA Group B (ID format) - This confirms the fix works
        expect(screen.getByText('TA Group B')).toBeInTheDocument();
    });

    it('handles data loading errors gracefully', async () => {
        // Mock failure when loading course data
        globalThis.fetch.mockRejectedValueOnce(new Error('Data Load Error'));

        render(
            <EnhancedTADashboard
                backendUrl={mockBackendUrl}
                getAuthHeaders={mockGetAuthHeaders}
                courses={mockCourses.courses}
            />
        );

        await waitFor(() => {
            expect(screen.getByText(/Data Load Error/i)).toBeInTheDocument();
        });
    });
});
