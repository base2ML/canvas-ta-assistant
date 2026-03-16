import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AssignmentStatusBreakdown from './AssignmentStatusBreakdown';

// ---------------------------------------------------------------------------
// Inline deadline editor tests — covers DEADLINE-UI-01
// ---------------------------------------------------------------------------

describe('Inline deadline editor', () => {
  const mockAssignment = {
    assignment_id: 1,
    assignment_name: 'HW 1',
    deadline_at: '2026-04-01T00:00:00Z',
    is_overdue: false,
    pending_submissions: 2,
    percentage_graded: 50,
    graded_submissions: 5,
    actually_submitted: 10,
    submitted_on_time: 4,
    submitted_late: 1,
    not_submitted: 2,
    ta_grading_breakdown: [],
    due_at: '2026-03-15T23:59:00Z',
    html_url: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    });
  });

  it('shows edit button for deadline', () => {
    render(
      <AssignmentStatusBreakdown
        courseId="c1"
        deadlines={[mockAssignment]}
        assignmentStats={[mockAssignment]}
        expandedAssignments={new Set()}
        onToggleExpanded={() => {}}
      />
    );
    expect(screen.getByRole('button', { name: /edit deadline/i })).toBeInTheDocument();
  });

  it('shows date input when edit button clicked', async () => {
    render(
      <AssignmentStatusBreakdown
        courseId="c1"
        deadlines={[mockAssignment]}
        assignmentStats={[mockAssignment]}
        expandedAssignments={new Set()}
        onToggleExpanded={() => {}}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /edit deadline/i }));
    // After clicking edit, a date input or text input should appear
    const input = screen.queryByRole('textbox') || screen.queryByDisplayValue(/2026/);
    expect(input).toBeInTheDocument();
  });

  it('calls PUT endpoint on save', async () => {
    render(
      <AssignmentStatusBreakdown
        courseId="c1"
        deadlines={[mockAssignment]}
        assignmentStats={[mockAssignment]}
        expandedAssignments={new Set()}
        onToggleExpanded={() => {}}
      />
    );

    // Click edit, then save
    fireEvent.click(screen.getByRole('button', { name: /edit deadline/i }));
    const saveButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(saveButton);

    // Verify fetch was called with PUT
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/dashboard/grading-deadlines'),
      expect.objectContaining({ method: 'PUT' })
    );
  });
});

// ---------------------------------------------------------------------------
// Overdue badge tests — covers DEADLINE-UI-02
// ---------------------------------------------------------------------------

describe('Overdue badge', () => {
  const baseMockAssignment = {
    assignment_id: 1,
    assignment_name: 'HW 1',
    deadline_at: '2026-01-01T00:00:00Z',
    is_overdue: false,
    pending_submissions: 0,
    percentage_graded: 100,
    graded_submissions: 10,
    actually_submitted: 10,
    submitted_on_time: 9,
    submitted_late: 1,
    not_submitted: 0,
    ta_grading_breakdown: [],
    due_at: '2026-01-01T23:59:00Z',
    html_url: null,
  };

  it('renders overdue badge when is_overdue=true and pending_submissions > 0', () => {
    const overdueAssignment = {
      ...baseMockAssignment,
      is_overdue: true,
      pending_submissions: 2,
      percentage_graded: 80,
      graded_submissions: 8,
    };
    render(
      <AssignmentStatusBreakdown
        courseId="c1"
        deadlines={[overdueAssignment]}
        assignmentStats={[overdueAssignment]}
        expandedAssignments={new Set()}
        onToggleExpanded={() => {}}
      />
    );
    expect(screen.getByText(/overdue/i)).toBeInTheDocument();
  });

  it('does NOT render overdue badge when is_overdue=false', () => {
    render(
      <AssignmentStatusBreakdown
        courseId="c1"
        deadlines={[baseMockAssignment]}
        assignmentStats={[baseMockAssignment]}
        expandedAssignments={new Set()}
        onToggleExpanded={() => {}}
      />
    );
    expect(screen.queryByText(/overdue/i)).not.toBeInTheDocument();
  });
});
