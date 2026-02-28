import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import EnrollmentTracking from './EnrollmentTracking';
import { BrowserRouter } from 'react-router-dom';

describe('EnrollmentTracking', () => {
    const mockCourses = [
        { id: '20960000000447574', name: 'Sandbox Course', course_code: 'CS101' }
    ];

    it('renders without crashing and shows page title', () => {
        render(
            <BrowserRouter>
                <EnrollmentTracking
                    courses={mockCourses}
                    onLoadCourses={vi.fn()}
                />
            </BrowserRouter>
        );

        expect(screen.getByText(/Enrollment Tracking/i)).toBeInTheDocument();
    });

    it('shows no course message when courses are empty', () => {
        render(
            <BrowserRouter>
                <EnrollmentTracking
                    courses={[]}
                    onLoadCourses={vi.fn()}
                />
            </BrowserRouter>
        );

        expect(screen.getByText(/No course configured/i)).toBeInTheDocument();
    });
});
