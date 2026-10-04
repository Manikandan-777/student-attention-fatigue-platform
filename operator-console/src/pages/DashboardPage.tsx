import React, { useState, useEffect, useRef } from 'react';
import { Users, Smile, Frown, AlertTriangle, Bell, Clock } from 'lucide-react';
import { useTelemetryWebSocket } from '../hooks/useTelemetryWebSocket';
import { StatCard } from '../components/StatCard';
import { ConnectionBanner } from '../components/ConnectionBanner';
import { LiveGrid } from '../components/LiveGrid';
import { AttentionTrendChart, AttentionDataPoint } from '../components/AttentionTrendChart';
import { DistributionChart } from '../components/DistributionChart';
import { FatigueTimelineChart, FatigueDataPoint } from '../components/FatigueTimelineChart';
import { RingBuffer } from '../utils/ringBuffer';

export const DashboardPage: React.FC = () => {
  const [selectedTrackId, setSelectedTrackId] = useState<number | null>(null);

  const {
    isConnected,
    snapshot,
    tracks,
    systemStatus,
  } = useTelemetryWebSocket();

  // Ring buffers for chart history (capacity 60 points)
  const attentionBufferRef = useRef(new RingBuffer<AttentionDataPoint>(60));
  const fatigueBufferRef = useRef(new RingBuffer<FatigueDataPoint>(60));

  const [attentionSeries, setAttentionSeries] = useState<AttentionDataPoint[]>([]);
  const [fatigueSeries, setFatigueSeries] = useState<FatigueDataPoint[]>([]);

  // Update chart series upon telemetry arrival
  useEffect(() => {
    if (!snapshot) return;

    const time = new Date().toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });

    // Find selected student score if any
    let studentScore: number | undefined;
    if (selectedTrackId !== null) {
      const t = tracks.find((tr) => tr.track_id === selectedTrackId);
      if (t) studentScore = t.attention_score;
    }

    attentionBufferRef.current.push({
      time,
      avgAttention: snapshot.avg_attention_score,
      studentAttention: studentScore,
    });

    fatigueBufferRef.current.push({
      time,
      fatiguedCount: snapshot.counts.fatigued,
    });

    setAttentionSeries(attentionBufferRef.current.getItems());
    setFatigueSeries(fatigueBufferRef.current.getItems());
  }, [snapshot, tracks, selectedTrackId]);

  const selectedTrack = tracks.find((t) => t.track_id === selectedTrackId);
  const privacyMode = systemStatus?.privacy_mode ?? true; // defaults to true per spec

  const counts = snapshot?.counts ?? {
    attentive: 0,
    distracted: 0,
    fatigued: 0,
    unknown: 0,
  };

  return (
    <div className="space-y-space-8">
      {/* Connection Banner */}
      <ConnectionBanner
        isWsConnected={isConnected}
        aiOffline={systemStatus?.ai_server === 'Offline'}
        cameraOffline={
          systemStatus?.cameras?.some((c) => c.state === 'Offline') ?? false
        }
      />

      {/* Snapshot Header Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-space-6">
        <StatCard
          label="Students Detected"
          value={snapshot?.students_detected ?? tracks.length}
          subtext="Active in session"
          icon={<Users className="w-5 h-5 text-accent-primary" />}
        />
        <StatCard
          label="Attentive"
          value={counts.attentive}
          subtext="On-task focus"
          icon={<Smile className="w-5 h-5 text-accent-success" />}
        />
        <StatCard
          label="Distracted"
          value={counts.distracted}
          subtext="Gaze/head deviation"
          icon={<Frown className="w-5 h-5 text-accent-primary" />}
        />
        <StatCard
          label="Fatigued"
          value={counts.fatigued}
          subtext="Drowsiness indicators"
          icon={<AlertTriangle className="w-5 h-5 text-accent-danger" />}
        />
        <StatCard
          label="Open Alerts"
          value={snapshot?.open_alerts ?? 0}
          subtext="Requiring review"
          icon={<Bell className="w-5 h-5 text-accent-danger" />}
        />
      </div>

      {/* Live Grid (Phase 18) */}
      <div className="bg-bg-surface border border-border-subtle rounded-radius-xl p-space-6 shadow-sm">
        <LiveGrid
          tracks={tracks}
          privacyMode={privacyMode}
          selectedTrackId={selectedTrackId}
          onSelectTrack={(id) =>
            setSelectedTrackId((prev) => (prev === id ? null : id))
          }
        />
      </div>

      {/* Real-Time Analytics & Charts (Phase 19) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-space-6">
        <AttentionTrendChart
          data={attentionSeries}
          selectedStudentLabel={selectedTrack ? selectedTrack.label : null}
        />
        <DistributionChart counts={counts} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-space-6">
        <FatigueTimelineChart data={fatigueSeries} />
        
        {/* System & Session Meta Card */}
        <div className="bg-bg-surface border border-border-subtle rounded-radius-xl p-space-6 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold text-text-primary mb-space-1">
              Active Session Status
            </h3>
            <p className="text-xs text-text-secondary mb-space-4">
              Telemetry streaming at 2 Hz target rate
            </p>

            <div className="space-y-space-3 text-sm">
              <div className="flex justify-between py-space-1 border-b border-border-subtle">
                <span className="text-text-secondary">Class Name</span>
                <span className="font-semibold text-text-primary">
                  {snapshot?.class_name ?? 'Monitoring Classroom'}
                </span>
              </div>
              <div className="flex justify-between py-space-1 border-b border-border-subtle">
                <span className="text-text-secondary">Average Score</span>
                <span className="font-semibold text-text-primary">
                  {Math.round(snapshot?.avg_attention_score ?? 0)}%
                </span>
              </div>
              <div className="flex justify-between py-space-1 border-b border-border-subtle">
                <span className="text-text-secondary">AI Pipeline Mode</span>
                <span className="font-semibold text-text-primary uppercase">
                  {systemStatus?.model_mode ?? 'heuristic'}
                </span>
              </div>
              <div className="flex justify-between py-space-1">
                <span className="text-text-secondary">Privacy Mode</span>
                <span className="font-semibold text-accent-primary">
                  {privacyMode ? 'Enabled (No Video)' : 'Disabled'}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center text-xs text-text-muted pt-space-4 mt-space-4 border-t border-border-subtle">
            <Clock className="w-4 h-4 mr-space-1" />
            <span>Updated live via WebSocket stream</span>
          </div>
        </div>
      </div>
    </div>
  );
};
