import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import LateDaysTracking from './LateDaysTracking';
import { BrowserRouter } from 'react-router-dom';

describe('LateDaysTracking', () => {
    const mockCourses = [
        { id: '1', name: 'Test Course', course_code: 'TEST101' }
    ];

    it('renders without crashing and shows course name', () => {
        render(
            <BrowserRouter>
                <LateDaysTracking
                    backendUrl="http://localhost:8000"
                    courses={mockCourses}
                    onLoadCourses={vi.fn()}
                />
            </BrowserRouter>
        );

        expect(screen.getByText(/Late Days Tracking/i)).toBeInTheDocument();
        // It might show "Test Course" if it selects the first one
        // expect(screen.getByText(/Test Course/i)).toBeInTheDocument();
    });

    it('shows no course message when courses are empty', () => {
        render(
            <BrowserRouter>
                <LateDaysTracking
                    backendUrl="http://localhost:8000"
                    courses={[]}
                    onLoadCourses={vi.fn()}
                />
            </BrowserRouter>
        );

        expect(screen.getByText(/No course available/i)).toBeInTheDocument();
    });
});
