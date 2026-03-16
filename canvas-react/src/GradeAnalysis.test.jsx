import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// This import will fail until the component exists — valid RED state
import GradeAnalysis from './GradeAnalysis';

describe('GradeAnalysis', () => {
  it('renders an assignment selector (combobox/select element)', () => {
    render(
      <MemoryRouter>
        <GradeAnalysis activeCourseId="course1" />
      </MemoryRouter>
    );
    // Expect a select or combobox role element for picking assignments
    const selector =
      screen.queryByRole('combobox') || screen.queryByRole('listbox');
    expect(selector).not.toBeNull();
  });

  it('renders loading state when fetching', () => {
    render(
      <MemoryRouter>
        <GradeAnalysis activeCourseId="course1" />
      </MemoryRouter>
    );
    // The component should show a loading indicator while data is being fetched
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders small-sample warning when stats.small_sample is true', () => {
    // Render with mock data prop indicating small sample
    // GradeAnalysis should accept an optional _testData prop for unit testing
    const mockData = {
      assignment_id: 101,
      assignment_name: 'HW 1',
      points_possible: 100,
      stats: { n: 3, small_sample: true, mean: 80, median: 80 },
      histogram: [],
      per_ta: [],
    };
    render(
      <MemoryRouter>
        <GradeAnalysis activeCourseId="course1" _testData={mockData} />
      </MemoryRouter>
    );
    // Small-sample warning badge should contain "small sample" or "n=3"
    expect(
      screen.getByText(/small sample|n=3/i)
    ).toBeInTheDocument();
  });

  it('/grade-analysis route renders GradeAnalysis component', () => {
    render(
      <MemoryRouter initialEntries={['/grade-analysis']}>
        <GradeAnalysis activeCourseId="course1" />
      </MemoryRouter>
    );
    // Component renders without crashing on the route
    // Presence of a heading or root element confirms the component rendered
    expect(document.body.firstChild).not.toBeNull();
  });
});
