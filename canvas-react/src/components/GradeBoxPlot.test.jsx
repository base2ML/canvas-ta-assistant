import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';

// This import will fail until the component exists — valid RED state
import GradeBoxPlot from './GradeBoxPlot';

describe('GradeBoxPlot', () => {
  it('renders an SVG element when stats.n >= 2', () => {
    const stats = { n: 5, q1: 60, median: 75, q3: 85, min: 50, max: 95, small_sample: false };
    const { container } = render(
      <GradeBoxPlot stats={stats} pointsPossible={100} />
    );
    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();
  });

  it('renders box and whisker line elements when stats.n >= 2', () => {
    const stats = { n: 5, q1: 60, median: 75, q3: 85, min: 50, max: 95, small_sample: false };
    const { container } = render(
      <GradeBoxPlot stats={stats} pointsPossible={100} />
    );
    // Box plot should have at least a rect (the IQR box) and line elements (whiskers)
    const rects = container.querySelectorAll('rect');
    const lines = container.querySelectorAll('line');
    expect(rects.length).toBeGreaterThanOrEqual(1);
    expect(lines.length).toBeGreaterThanOrEqual(1);
  });

  it('renders nothing when stats.n < 2', () => {
    const stats = { n: 1, small_sample: true };
    const { container } = render(
      <GradeBoxPlot stats={stats} pointsPossible={100} />
    );
    // Should render nothing (null) for n < 2
    const svg = container.querySelector('svg');
    expect(svg).toBeNull();
  });
});
