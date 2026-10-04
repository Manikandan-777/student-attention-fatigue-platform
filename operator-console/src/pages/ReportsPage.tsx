import React, { useEffect, useState } from 'react';
import { FileText, Download, Calendar, Clock, Users, CheckCircle2 } from 'lucide-react';
import apiClient from '../api/client';
import { SessionReport } from '../types';
import { API_BASE_URL } from '../config';

export const ReportsPage: React.FC = () => {
  const [reports, setReports] = useState<SessionReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<SessionReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const fetchReports = async () => {
      setIsLoading(true);
      try {
        const response = await apiClient.get<SessionReport[]>('/reports');
        setReports(response.data);
        if (response.data.length > 0) {
          setSelectedReport(response.data[0]);
        }
      } catch (err) {
        console.error('Failed to fetch session reports:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchReports();
  }, []);

  const handleDownload = (sessionId: number, format: 'csv' | 'pdf') => {
    const downloadUrl = `${API_BASE_URL}/reports/${sessionId}/export?format=${format}`;
    window.open(downloadUrl, '_blank');
  };

  return (
    <div className="space-y-space-8">
      <div className="flex items-center space-x-space-4">
        <FileText className="w-5 h-5 text-accent-primary" aria-hidden="true" />
        <h2 className="text-lg font-bold text-text-primary">
          Session Reports & Analytics History
        </h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-space-8">
        {/* Reports list sidebar */}
        <div className="bg-bg-surface border border-border-subtle rounded-radius-xl p-space-6 shadow-sm space-y-space-4">
          <h3 className="text-sm font-bold text-text-primary">
            Past Sessions ({reports.length})
          </h3>

          {isLoading ? (
            <p className="text-sm text-text-muted">Loading reports...</p>
          ) : reports.length === 0 ? (
            <p className="text-sm text-text-muted">No completed sessions found.</p>
          ) : (
            <div className="space-y-space-3" role="listbox" aria-label="Past session reports">
              {reports.map((rep) => (
                <button
                  key={rep.session_id}
                  type="button"
                  onClick={() => setSelectedReport(rep)}
                  className={`w-full text-left p-space-4 rounded-radius-lg border transition-all ${
                    selectedReport?.session_id === rep.session_id
                      ? 'border-accent-primary bg-bg-info shadow-sm'
                      : 'border-border-subtle hover:border-border-strong bg-bg-surface'
                  }`}
                  aria-selected={selectedReport?.session_id === rep.session_id}
                >
                  <div className="flex justify-between items-center mb-space-1">
                    <span className="text-sm font-bold text-text-primary">
                      {rep.class_name}
                    </span>
                    <span className="text-xs text-text-muted">
                      #{rep.session_id}
                    </span>
                  </div>
                  <div className="flex items-center space-x-space-3 text-xs text-text-secondary">
                    <span className="flex items-center">
                      <Calendar className="w-3.5 h-3.5 mr-space-1 text-text-muted" />
                      {rep.date}
                    </span>
                    <span className="flex items-center">
                      <Clock className="w-3.5 h-3.5 mr-space-1 text-text-muted" />
                      {rep.duration_min} min
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Selected report detail */}
        <div className="lg:col-span-2 space-y-space-6">
          {selectedReport ? (
            <div className="bg-bg-surface border border-border-subtle rounded-radius-xl p-space-8 shadow-sm space-y-space-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-space-6 border-b border-border-subtle gap-space-4">
                <div>
                  <h3 className="text-xl font-bold text-text-primary">
                    {selectedReport.class_name}
                  </h3>
                  <p className="text-xs text-text-secondary mt-space-1">
                    Date: {selectedReport.date} | Time: {selectedReport.start} - {selectedReport.end} ({selectedReport.duration_min} min)
                  </p>
                </div>

                <div className="flex items-center space-x-space-3">
                  <button
                    type="button"
                    onClick={() => handleDownload(selectedReport.session_id, 'csv')}
                    className="inline-flex items-center px-space-3 py-space-2 text-xs font-semibold text-text-body bg-bg-surface border border-border-strong rounded-radius-lg hover:bg-bg-info transition-colors focus:ring-2 focus:ring-accent-primary"
                  >
                    <Download className="w-3.5 h-3.5 mr-space-1" />
                    CSV Export
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDownload(selectedReport.session_id, 'pdf')}
                    className="inline-flex items-center px-space-3 py-space-2 text-xs font-semibold text-bg-surface bg-accent-primary rounded-radius-lg hover:opacity-90 transition-opacity focus:ring-2 focus:ring-accent-primary shadow-sm"
                  >
                    <Download className="w-3.5 h-3.5 mr-space-1" />
                    PDF Report
                  </button>
                </div>
              </div>

              {/* Aggregates overview */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-space-4">
                <div className="p-space-4 bg-bg-surface border border-border-subtle rounded-radius-lg">
                  <span className="text-xs text-text-secondary">Students</span>
                  <div className="text-lg font-bold text-text-primary mt-space-1">
                    {selectedReport.students}
                  </div>
                </div>
                <div className="p-space-4 bg-bg-surface border border-border-subtle rounded-radius-lg">
                  <span className="text-xs text-text-secondary">Avg Attention</span>
                  <div className="text-lg font-bold text-accent-primary mt-space-1">
                    {Math.round(selectedReport.avg_attention_score)}%
                  </div>
                </div>
                <div className="p-space-4 bg-bg-surface border border-border-subtle rounded-radius-lg">
                  <span className="text-xs text-text-secondary">Attentive Count</span>
                  <div className="text-lg font-bold text-accent-success mt-space-1">
                    {selectedReport.attention.attentive}
                  </div>
                </div>
                <div className="p-space-4 bg-bg-surface border border-border-subtle rounded-radius-lg">
                  <span className="text-xs text-text-secondary">Fatigued Count</span>
                  <div className="text-lg font-bold text-accent-danger mt-space-1">
                    {selectedReport.fatigue.fatigued}
                  </div>
                </div>
              </div>

              {/* Per student table */}
              <div>
                <h4 className="text-sm font-bold text-text-primary mb-space-3 flex items-center">
                  <Users className="w-4 h-4 mr-space-2 text-accent-primary" />
                  Per-Student Summary
                </h4>
                <div className="overflow-x-auto border border-border-subtle rounded-radius-lg">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-bg-surface border-b border-border-subtle">
                      <tr>
                        <th className="p-space-3 font-semibold text-text-body">Label</th>
                        <th className="p-space-3 font-semibold text-text-body">Mean Attention</th>
                        <th className="p-space-3 font-semibold text-text-body">Fatigue Index</th>
                        <th className="p-space-3 font-semibold text-text-body">Fatigue Ind.</th>
                        <th className="p-space-3 font-semibold text-text-body">Distraction Ind.</th>
                        <th className="p-space-3 font-semibold text-text-body">Alerts</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-subtle">
                      {selectedReport.per_student.map((st) => (
                        <tr key={st.label} className="hover:bg-bg-surface">
                          <td className="p-space-3 font-bold text-text-primary">{st.label}</td>
                          <td className="p-space-3">{Math.round(st.attention_mean)}%</td>
                          <td className="p-space-3">{st.fatigue_index_mean.toFixed(2)}</td>
                          <td className="p-space-3">{st.fatigue_indicators}</td>
                          <td className="p-space-3">{st.distraction_indicators}</td>
                          <td className="p-space-3">
                            {st.alerts > 0 ? (
                              <span className="text-accent-danger font-semibold">{st.alerts}</span>
                            ) : (
                              <span className="text-text-muted">0</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Mandatory Ethical Notice Footer */}
              <div className="pt-space-4 border-t border-border-subtle text-xs text-text-muted italic flex items-center">
                <CheckCircle2 className="w-4 h-4 mr-space-2 text-accent-success flex-shrink-0" />
                <span>AI-generated indicators to support teacher observation; not a diagnosis or disciplinary record.</span>
              </div>
            </div>
          ) : (
            <div className="bg-bg-surface border border-border-subtle rounded-radius-xl p-space-12 text-center text-text-muted shadow-sm">
              Select a session report from the left to view details and export files.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
