import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

// This import will fail until the component exists (valid RED state)
import GradingScheduleSummary from './GradingScheduleSummary';

describe('GradingScheduleSummary', () => {
  const mockData = {
    assignments: [
      {
        assignment_id: 1,
        assignment_name: 'HW 1',
        deadline_at: '2026-04-01T00:00:00Z',
        is_overdue: false,
        pending_submissions: 2,
      },
    ],
  };

  it('renders assignment names', () => {
    render(<GradingScheduleSummary data={mockData} />);
    expect(screen.getByText('HW 1')).toBeInTheDocument();
  });

  it('renders grading deadline', () => {
    render(<GradingScheduleSummary data={mockData} />);
    expect(screen.getByText(/2026-04-01|Apr 1/i)).toBeInTheDocument();
  });

  it('renders overdue badge when is_overdue=true', () => {
    const overdueData = {
      assignments: [{ ...mockData.assignments[0], is_overdue: true, pending_submissions: 1 }],
    };
    render(<GradingScheduleSummary data={overdueData} />);
    expect(screen.getByText(/overdue/i)).toBeInTheDocument();
  });
});
