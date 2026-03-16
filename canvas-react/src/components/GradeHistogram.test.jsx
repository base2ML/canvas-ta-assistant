import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';

// This import will fail until the component exists — valid RED state
import GradeHistogram from './GradeHistogram';

describe('GradeHistogram', () => {
  const bins = [
    { bin_start: 0, bin_end: 10, count: 3, label: '0–10' },
    { bin_start: 10, bin_end: 20, count: 1, label: '10–20' },
  ];

  it('renders correct number of SVG rect elements equal to bins.length', () => {
    const { container } = render(<GradeHistogram bins={bins} pointsPossible={100} />);
    const rects = container.querySelectorAll('rect');
    expect(rects.length).toBe(bins.length);
  });

  it('renders nothing when bins is empty', () => {
    const { container } = render(<GradeHistogram bins={[]} pointsPossible={100} />);
    // No rect elements when bins is empty
    const rects = container.querySelectorAll('rect');
    expect(rects.length).toBe(0);
  });

  it('renders an SVG element when bins are provided', () => {
    const { container } = render(<GradeHistogram bins={bins} pointsPossible={100} />);
    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();
  });
});
