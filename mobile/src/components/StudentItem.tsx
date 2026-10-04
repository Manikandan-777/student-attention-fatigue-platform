import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { THEME } from '../theme';
import { StatusBadge } from './StatusBadge';
import { TrackResultLite } from '../types';

interface StudentItemProps {
  student: TrackResultLite;
  onPress?: () => void;
}

export const StudentItem: React.FC<StudentItemProps> = ({ student, onPress }) => {
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.7}
      accessibilityRole="button"
      accessibilityLabel={`Student ${student.label}, Attention: ${student.attention_status}, Fatigue: ${student.fatigue_status}`}
      style={styles.container}
    >
      <View style={styles.leftCol}>
        <Text style={styles.label}>{student.label}</Text>
        <Text style={styles.confidence}>
          Confidence: {Math.round(student.confidence * 100)}%
        </Text>
      </View>

      <View style={styles.rightCol}>
        <View style={styles.badgeRow}>
          <StatusBadge status={student.attention_status} size="sm" />
          <View style={styles.badgeSpacer} />
          <StatusBadge status={student.fatigue_status} size="sm" />
        </View>
        <Text style={styles.score}>
          Score: {Math.round(student.attention_score)}%
        </Text>
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    minHeight: THEME.spacing.space11, // Minimum 44dp touch target per UI-7
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    borderRadius: THEME.radius.lg,
    padding: THEME.spacing.space6,
    marginBottom: THEME.spacing.space4,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  leftCol: {
    flex: 1,
  },
  label: {
    fontSize: THEME.typography.sizes.base,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
  },
  confidence: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textMuted,
    marginTop: THEME.spacing.space1,
  },
  rightCol: {
    alignItems: 'flex-end',
  },
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  badgeSpacer: {
    width: THEME.spacing.space2,
  },
  score: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textSecondary,
    fontWeight: '600',
    marginTop: THEME.spacing.space1,
  },
});
