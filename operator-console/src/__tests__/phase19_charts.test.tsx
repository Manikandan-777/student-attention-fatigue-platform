import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RingBuffer } from '../utils/ringBuffer';
import { AttentionTrendChart } from '../components/AttentionTrendChart';
import { DistributionChart } from '../components/DistributionChart';
import { FatigueTimelineChart } from '../components/FatigueTimelineChart';

describe('Phase 19: Real-Time Charts & Analytics', () => {
  describe('RingBuffer Utility', () => {
    it('maintains bounded capacity and evicts oldest items in FIFO order', () => {
      const buffer = new RingBuffer<number>(3);
      buffer.push(10);
      buffer.push(20);
      buffer.push(30);

      expect(buffer.size()).toBe(3);
      expect(buffer.getItems()).toEqual([10, 20, 30]);

      // Push 4th item -> 10 should be evicted
      buffer.push(40);
      expect(buffer.size()).toBe(3);
      expect(buffer.getItems()).toEqual([20, 30, 40]);

      buffer.push(50);
      expect(buffer.getItems()).toEqual([30, 40, 50]);

      buffer.clear();
      expect(buffer.size()).toBe(0);
      expect(buffer.getItems()).toEqual([]);
    });

    it('simulates high-frequency feed without memory bloat', () => {
      const buffer = new RingBuffer<{ val: number }>(60);
      // Simulate 10,000 pushes
      for (let i = 0; i < 10000; i++) {
        buffer.push({ val: i });
      }
      expect(buffer.size()).toBe(60);
      const items = buffer.getItems();
      expect(items[items.length - 1].val).toBe(9999);
      expect(items[0].val).toBe(9940);
    });
  });

  describe('AttentionTrendChart', () => {
    it('renders empty placeholder when no points exist', () => {
      render(<AttentionTrendChart data={[]} />);
      expect(screen.getByText(/Waiting for telemetry samples/i)).toBeInTheDocument();
    });

    it('renders chart and accessible tabular alternative when data is present', () => {
      const data = [
        { time: '10:00:00', avgAttention: 80, studentAttention: 85 },
        { time: '10:00:01', avgAttention: 82, studentAttention: 88 },
      ];

      render(
        <AttentionTrendChart data={data} selectedStudentLabel="S001" />
      );

      expect(screen.getByText('Attention Score Trend')).toBeInTheDocument();
      expect(screen.getAllByText('82%').length).toBeGreaterThanOrEqual(1); // latest avg in header and table
      expect(screen.getByText('Accessible data view (tabular)')).toBeInTheDocument();
      expect(screen.getByText('10:00:00')).toBeInTheDocument();
      expect(screen.getByText('10:00:01')).toBeInTheDocument();
    });
  });

  describe('DistributionChart', () => {
    it('renders distribution counts and accessible table', () => {
      const counts = {
        attentive: 25,
        distracted: 5,
        fatigued: 2,
        unknown: 1,
      };

      render(<DistributionChart counts={counts} />);

      expect(screen.getByText('Student Status Distribution')).toBeInTheDocument();
      expect(screen.getByText('33')).toBeInTheDocument(); // Total Active = 33
      expect(screen.getByText('Accessible summary table')).toBeInTheDocument();
      expect(screen.getByText('25')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
    });
  });

  describe('FatigueTimelineChart', () => {
    it('renders fatigue timeline chart and accessible tabular data', () => {
      const data = [
        { time: '10:00:00', fatiguedCount: 1 },
        { time: '10:00:02', fatiguedCount: 3 },
      ];

      render(<FatigueTimelineChart data={data} />);

      expect(screen.getByText('Fatigue Timeline')).toBeInTheDocument();
      expect(screen.getAllByText('3').length).toBeGreaterThanOrEqual(1); // Latest count
      expect(screen.getByText('10:00:02')).toBeInTheDocument();
    });
  });
});
