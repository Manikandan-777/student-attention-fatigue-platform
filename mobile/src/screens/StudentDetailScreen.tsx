import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import { THEME } from '../theme';
import { StatusBadge } from '../components/StatusBadge';
import { TrackResultLite } from '../types';

interface StudentDetailScreenProps {
  student: TrackResultLite;
  onViewReport?: () => void;
  onBack?: () => void;
}

export const StudentDetailScreen: React.FC<StudentDetailScreenProps> = ({
  student,
  onViewReport,
  onBack,
}) => {
  return (
    <ScrollView style={styles.container}>
      <View style={styles.content}>
        {onBack && (
          <TouchableOpacity
            style={styles.backButton}
            onPress={onBack}
            accessibilityRole="button"
            accessibilityLabel="Back to Student List"
          >
            <Text style={styles.backButtonText}>← Back to Students</Text>
          </TouchableOpacity>
        )}

        <Text style={styles.studentTitle}>Student {student.label}</Text>

        <View style={styles.card}>
          <Text style={styles.sectionHeader}>Current Status</Text>
          <View style={styles.divider} />

          <View style={styles.row}>
            <Text style={styles.rowLabel}>Attention:</Text>
            <StatusBadge status={student.attention_status} size="sm" />
          </View>

          <View style={styles.row}>
            <Text style={styles.rowLabel}>Fatigue:</Text>
            <StatusBadge status={student.fatigue_status} size="sm" />
          </View>
        </View>

        <View style={styles.card}>
          <Text style={styles.sectionHeader}>Confidence</Text>
          <View style={styles.divider} />
          <Text style={styles.confidenceValue}>
            {Math.round(student.confidence * 100)}%
          </Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.sectionHeader}>Session Statistics</Text>
          <View style={styles.divider} />

          <View style={styles.statRow}>
            <Text style={styles.statLabel}>Attention Score</Text>
            <Text style={styles.statValue}>
              {Math.round(student.attention_score)}%
            </Text>
          </View>

          <View style={styles.statRow}>
            <Text style={styles.statLabel}>Fatigue Indicators</Text>
            <Text style={styles.statValue}>
              {student.fatigue_status === 'Fatigued' ? '1+' : '0'}
            </Text>
          </View>

          <View style={styles.statRow}>
            <Text style={styles.statLabel}>Distraction Indicators</Text>
            <Text style={styles.statValue}>
              {student.attention_status === 'Distracted' ? '1+' : '0'}
            </Text>
          </View>

          <View style={styles.statRow}>
            <Text style={styles.statLabel}>Number of Alerts</Text>
            <Text style={styles.statValue}>
              {student.fatigue_status === 'Fatigued' || student.attention_status === 'Distracted' ? '1' : '0'}
            </Text>
          </View>

          {onViewReport && (
            <TouchableOpacity
              style={styles.actionButton}
              onPress={onViewReport}
              accessibilityRole="button"
              accessibilityLabel="View Detailed Report"
            >
              <Text style={styles.actionButtonText}>
                [ View Detailed Report ]
              </Text>
            </TouchableOpacity>
          )}
        </View>
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
  backButton: {
    minHeight: THEME.spacing.space11,
    justifyContent: 'center',
    marginBottom: THEME.spacing.space4,
  },
  backButtonText: {
    color: THEME.colors.accentPrimary,
    fontSize: THEME.typography.sizes.sm,
    fontWeight: '600',
  },
  studentTitle: {
    fontSize: THEME.typography.sizes.xl,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
    marginBottom: THEME.spacing.space6,
  },
  card: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    borderRadius: THEME.radius.xl,
    padding: THEME.spacing.space8,
    marginBottom: THEME.spacing.space6,
  },
  sectionHeader: {
    fontSize: THEME.typography.sizes.sm,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
  },
  divider: {
    height: 1,
    backgroundColor: THEME.colors.borderSubtle,
    marginVertical: THEME.spacing.space4,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: THEME.spacing.space2,
  },
  rowLabel: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.textBody,
  },
  confidenceValue: {
    fontSize: THEME.typography.sizes.lg,
    fontWeight: 'bold',
    color: THEME.colors.accentPrimary,
  },
  statRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: THEME.spacing.space2,
  },
  statLabel: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.textBody,
  },
  statValue: {
    fontSize: THEME.typography.sizes.sm,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
  },
  actionButton: {
    minHeight: THEME.spacing.space11, // 44dp
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: THEME.spacing.space4,
  },
  actionButtonText: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.accentPrimary,
    fontWeight: 'bold',
  },
});
