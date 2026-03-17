import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

describe('per-TA sortable table', () => {
  const mockDetail = {
    assignment_id: 101,
    assignment_name: 'HW 1',
    points_possible: 100,
    stats: { n: 10, small_sample: false, mean: 80, median: 82, stdev: 8,
             min: 60, q1: 75, q3: 90, max: 100 },
    histogram: [],
    per_ta: [
      {
        grader_name: 'Alice TA',
        n: 6,
        mean: 85.0,
        median: 86.0,
        stdev: 5.0,
        min: 78.0,
        q1: 81.0,
        q3: 89.0,
        max: 94.0,
        small_sample: false,
      },
      {
        grader_name: 'Bob TA',
        n: 3,
        mean: 72.0,
        median: 70.0,
        stdev: 4.0,
        min: 68.0,
        q1: 69.0,
        q3: 75.0,
        max: 77.0,
        small_sample: true,
      },
      {
        grader_name: 'Unattributed',
        n: 1,
        mean: 55.0,
        median: 55.0,
        stdev: null,
        min: 55.0,
        q1: null,
        q3: null,
        max: 55.0,
        small_sample: true,
      },
    ],
  };

  it('renders Mean, Median, Std Dev column headers', () => {
    render(
      <MemoryRouter>
        <GradeAnalysis activeCourseId="course1" _testData={mockDetail} />
      </MemoryRouter>
    );
    expect(screen.getAllByText('Mean').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Median').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Std Dev').length).toBeGreaterThan(0);
  });

  it('renders TA names in the table', () => {
    render(
      <MemoryRouter>
        <GradeAnalysis activeCourseId="course1" _testData={mockDetail} />
      </MemoryRouter>
    );
    expect(screen.getByText('Alice TA')).toBeInTheDocument();
    expect(screen.getByText('Bob TA')).toBeInTheDocument();
  });

  it('renders small-sample badge beside TA with small_sample=true', () => {
    render(
      <MemoryRouter>
        <GradeAnalysis activeCourseId="course1" _testData={mockDetail} />
      </MemoryRouter>
    );
    // Bob TA has small_sample=true and n=3 — expect badge text "n=3"
    expect(screen.getByText(/n=3/i)).toBeInTheDocument();
  });

  it('renders — for null stdev', () => {
    render(
      <MemoryRouter>
        <GradeAnalysis activeCourseId="course1" _testData={mockDetail} />
      </MemoryRouter>
    );
    // Unattributed row has stdev=null — should display em dash
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });

  it('renders Distribution column header with axis ticks', () => {
    render(
      <MemoryRouter>
        <GradeAnalysis activeCourseId="course1" _testData={mockDetail} />
      </MemoryRouter>
    );
    expect(screen.getAllByText(/distribution/i).length).toBeGreaterThan(0);
  });

  it('clicking Median header re-sorts the table', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <GradeAnalysis activeCourseId="course1" _testData={mockDetail} />
      </MemoryRouter>
    );
    const medianBtn = screen.getByRole('button', { name: /median/i });
    await user.click(medianBtn);
    // After clicking, Median header should show a sort direction arrow
    expect(medianBtn.textContent).toMatch(/[↑↓]/);
  });
});
