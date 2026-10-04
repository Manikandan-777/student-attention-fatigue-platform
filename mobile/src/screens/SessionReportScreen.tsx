import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, ActivityIndicator } from 'react-native';
import { THEME } from '../theme';
import { ApiService } from '../services/api';
import { SessionReport } from '../types';

export const SessionReportScreen: React.FC = () => {
  const [reports, setReports] = useState<SessionReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<SessionReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadReports = async () => {
      try {
        const data = await ApiService.getReports();
        setReports(data);
        if (data.length > 0) {
          setSelectedReport(data[0]);
        }
      } catch {
        // offline
      } finally {
        setLoading(false);
      }
    };
    loadReports();
  }, []);

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator color={THEME.colors.accentPrimary} />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.header}>Session Reports</Text>

        {reports.length === 0 ? (
          <View style={styles.card}>
            <Text style={styles.emptyText}>No session reports available.</Text>
          </View>
        ) : (
          <>
            {/* History Selector Chips */}
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow}>
              {reports.map((rep) => (
                <TouchableOpacity
                  key={rep.session_id}
                  style={[
                    styles.chip,
                    selectedReport?.session_id === rep.session_id && styles.chipActive,
                  ]}
                  onPress={() => setSelectedReport(rep)}
                  accessibilityRole="button"
                  accessibilityLabel={`Session #${rep.session_id}, ${rep.class_name}`}
                >
                  <Text
                    style={[
                      styles.chipText,
                      selectedReport?.session_id === rep.session_id && styles.chipTextActive,
                    ]}
                  >
                    #{rep.session_id} {rep.class_name}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>

            {selectedReport && (
              <View style={styles.card}>
                <Text style={styles.reportTitle}>CLASSROOM SESSION REPORT</Text>
                <View style={styles.divider} />

                <Text style={styles.metaText}>Class: {selectedReport.class_name}</Text>
                <Text style={styles.metaText}>Duration: {selectedReport.duration_min} minutes</Text>
                <Text style={styles.metaText}>Students: {selectedReport.students}</Text>
                <Text style={styles.metaText}>Date: {selectedReport.date} ({selectedReport.start} - {selectedReport.end})</Text>

                <View style={styles.divider} />

                <Text style={styles.sectionTitle}>Attention</Text>
                <View style={styles.metricRow}>
                  <Text style={styles.metricLabel}>Attentive:</Text>
                  <Text style={[styles.metricValue, { color: THEME.colors.accentSuccess }]}>
                    {selectedReport.attention.attentive}
                  </Text>
                </View>
                <View style={styles.metricRow}>
                  <Text style={styles.metricLabel}>Distracted:</Text>
                  <Text style={[styles.metricValue, { color: THEME.colors.accentPrimary }]}>
                    {selectedReport.attention.distracted}
                  </Text>
                </View>
                <View style={styles.metricRow}>
                  <Text style={styles.metricLabel}>Class Average:</Text>
                  <Text style={styles.metricValue}>
                    {Math.round(selectedReport.avg_attention_score)}%
                  </Text>
                </View>

                <View style={styles.divider} />

                <Text style={styles.sectionTitle}>Fatigue</Text>
                <View style={styles.metricRow}>
                  <Text style={styles.metricLabel}>Normal:</Text>
                  <Text style={[styles.metricValue, { color: THEME.colors.accentSuccess }]}>
                    {selectedReport.fatigue.normal}
                  </Text>
                </View>
                <View style={styles.metricRow}>
                  <Text style={styles.metricLabel}>Fatigue:</Text>
                  <Text style={[styles.metricValue, { color: THEME.colors.accentDanger }]}>
                    {selectedReport.fatigue.fatigued}
                  </Text>
                </View>

                <View style={styles.divider} />

                <Text style={styles.sectionTitle}>Alerts</Text>
                <View style={styles.metricRow}>
                  <Text style={styles.metricLabel}>Total Alerts:</Text>
                  <Text style={styles.metricValue}>{selectedReport.alerts_total}</Text>
                </View>

                {/* Mandatory ethical footer */}
                <View style={styles.footerContainer}>
                  <Text style={styles.footerNotice}>
                    AI-generated indicators to support teacher observation; not a diagnosis or disciplinary record.
                  </Text>
                </View>
              </View>
            )}
          </>
        )}
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME.colors.bgApp,
  },
  content: {
    padding: THEME.spacing.space8,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    fontSize: THEME.typography.sizes.lg,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
    marginBottom: THEME.spacing.space6,
  },
  chipRow: {
    flexDirection: 'row',
    marginBottom: THEME.spacing.space6,
  },
  chip: {
    minHeight: THEME.spacing.space11, // 44dp
    paddingHorizontal: THEME.spacing.space6,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    borderRadius: THEME.radius.pill,
    marginRight: THEME.spacing.space3,
  },
  chipActive: {
    backgroundColor: THEME.colors.accentPrimary,
    borderColor: THEME.colors.accentPrimary,
  },
  chipText: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textSecondary,
    fontWeight: '600',
  },
  chipTextActive: {
    color: THEME.colors.bgSurface,
  },
  card: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    borderRadius: THEME.radius.xl,
    padding: THEME.spacing.space8,
  },
  emptyText: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.textMuted,
    textAlign: 'center',
  },
  reportTitle: {
    fontSize: THEME.typography.sizes.base,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
  },
  metaText: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.textBody,
    marginBottom: THEME.spacing.space1,
  },
  sectionTitle: {
    fontSize: THEME.typography.sizes.sm,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
    marginBottom: THEME.spacing.space2,
  },
  divider: {
    height: 1,
    backgroundColor: THEME.colors.borderSubtle,
    marginVertical: THEME.spacing.space4,
  },
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: THEME.spacing.space1,
  },
  metricLabel: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.textBody,
  },
  metricValue: {
    fontSize: THEME.typography.sizes.sm,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
  },
  footerContainer: {
    marginTop: THEME.spacing.space8,
    paddingTop: THEME.spacing.space4,
    borderTopWidth: 1,
    borderTopColor: THEME.colors.borderSubtle,
  },
  footerNotice: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textMuted,
    fontStyle: 'italic',
    textAlign: 'center',
  },
});
