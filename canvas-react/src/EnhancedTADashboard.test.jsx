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

    const mockCourses = [
        { id: '1', name: 'Course 1' },
        { id: '2', name: 'Course 2' }
    ];

    const mockAssignments = {
        assignments: [
            { id: 101, name: 'Assignment 1', due_at: '2023-01-01' }
        ]
    };

    const mockSubmissions = {
        submissions: [
            { id: 1, user_id: 1, assignment_id: 101, workflow_state: 'graded' },
            { id: 2, user_id: 2, assignment_id: 101, workflow_state: 'submitted' }
        ]
    };

    const mockGroups = {
        groups: [
            { name: 'TA Group A', members: [{ user_id: 1 }] },
            { name: 'TA Group B', members: [2] }
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
                courses={mockCourses}
            />
        );

        expect(screen.getByText(/TA Grading Dashboard/i)).toBeInTheDocument();
        expect(screen.getByText('Course 1')).toBeInTheDocument();
    });

    it('loads course data and handles mixed group member formats', async () => {
        // Mock API responses for course data
        globalThis.fetch
            .mockResolvedValueOnce({ ok: true, json: async () => mockAssignments })
            .mockResolvedValueOnce({ ok: true, json: async () => mockSubmissions })
            .mockResolvedValueOnce({ ok: true, json: async () => mockGroups });

        render(
            <EnhancedTADashboard
                backendUrl={mockBackendUrl}
                courses={mockCourses}
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
                courses={mockCourses}
            />
        );

        await waitFor(() => {
            expect(screen.getByText(/Data Load Error/i)).toBeInTheDocument();
        });
    });
});
