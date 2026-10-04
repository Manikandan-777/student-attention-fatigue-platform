import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { AlertFeed } from '../components/AlertFeed';
import { AlertItem } from '../components/AlertItem';
import { Alert } from '../types';

const mockAlerts: Alert[] = [
  {
    id: 1,
    session_id: 12,
    track_id: 3,
    label: 'S003',
    type: 'fatigue',
    status: 'New',
    message: 'Repeated fatigue-related indicators during the current session.',
    confidence: 0.92,
    created_at: '2026-10-03T10:15:00Z',
    viewed_at: null,
    resolved_at: null,
  },
  {
    id: 2,
    session_id: 12,
    track_id: 4,
    label: 'S004',
    type: 'distraction',
    status: 'Viewed',
    message: 'Repeated gaze deviations away from frontal task area.',
    confidence: 0.88,
    created_at: '2026-10-03T10:16:00Z',
    viewed_at: '2026-10-03T10:16:30Z',
    resolved_at: null,
  },
  {
    id: 3,
    session_id: 12,
    track_id: 5,
    label: 'S005',
    type: 'fatigue',
    status: 'Resolved',
    message: 'Repeated fatigue-related indicators during the current session.',
    confidence: 0.95,
    created_at: '2026-10-03T10:14:00Z',
    viewed_at: '2026-10-03T10:14:30Z',
    resolved_at: '2026-10-03T10:17:00Z',
  },
];

describe('Phase 20: Alert Log & Event Feed', () => {
  it('renders alert item with non-stigmatizing informational copy (D8)', () => {
    const onUpdate = vi.fn();
    render(<AlertItem alert={mockAlerts[0]} onUpdateStatus={onUpdate} />);

    expect(screen.getByText('Student S003')).toBeInTheDocument();
    expect(screen.getByText(/fatigue-related indicators/i)).toBeInTheDocument();
    // Verify prohibited diagnostic words are absent
    expect(screen.queryByText(/asleep/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/lazy/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/sleeping/i)).not.toBeInTheDocument();

    expect(screen.getByRole('button', { name: /Mark alert 1 as Viewed/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Resolve alert 1/i })).toBeInTheDocument();
  });

  it('triggers onUpdateStatus callback when action buttons are clicked', async () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined);
    render(<AlertItem alert={mockAlerts[0]} onUpdateStatus={onUpdate} />);

    fireEvent.click(screen.getByRole('button', { name: /Mark alert 1 as Viewed/i }));
    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalledWith(1, 'Viewed');
    });

    fireEvent.click(screen.getByRole('button', { name: /Resolve alert 1/i }));
    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalledWith(1, 'Resolved');
    });
  });

  it('orders alerts in reverse-chronological order (newest first)', () => {
    const onUpdate = vi.fn();
    render(<AlertFeed alerts={mockAlerts} onUpdateStatus={onUpdate} />);

    const alertHeadings = screen.getAllByText(/Student S00/i);
    // Alert #2 created at 10:16, Alert #1 at 10:15, Alert #3 at 10:14
    expect(alertHeadings[0]).toHaveTextContent('Student S004');
    expect(alertHeadings[1]).toHaveTextContent('Student S003');
    expect(alertHeadings[2]).toHaveTextContent('Student S005');
  });

  it('filters alerts by status tabs', () => {
    const onUpdate = vi.fn();
    render(<AlertFeed alerts={mockAlerts} onUpdateStatus={onUpdate} />);

    expect(screen.getByText('3 shown')).toBeInTheDocument();

    // Click "New" filter
    fireEvent.click(screen.getByRole('button', { name: 'New' }));
    expect(screen.getByText('1 shown')).toBeInTheDocument();
    expect(screen.getByText('Student S003')).toBeInTheDocument();
    expect(screen.queryByText('Student S004')).not.toBeInTheDocument();

    // Click "Resolved" filter
    fireEvent.click(screen.getByRole('button', { name: 'Resolved' }));
    expect(screen.getByText('1 shown')).toBeInTheDocument();
    expect(screen.getByText('Student S005')).toBeInTheDocument();
  });

  it('has aria-live polite region for accessibility', () => {
    const onUpdate = vi.fn();
    render(<AlertFeed alerts={mockAlerts} onUpdateStatus={onUpdate} />);

    const liveRegion = screen.getByRole('region', { name: /Live alert updates/i });
    expect(liveRegion).toHaveAttribute('aria-live', 'polite');
  });

  it('displays empty state when no alerts exist', () => {
    const onUpdate = vi.fn();
    render(<AlertFeed alerts={[]} onUpdateStatus={onUpdate} />);

    expect(screen.getByText('No alerts found')).toBeInTheDocument();
  });
});
