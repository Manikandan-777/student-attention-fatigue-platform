import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Bell, ChevronRight } from 'lucide-react-native';

interface RecentAlertCardProps {
  openAlerts: number;
  fatigueCount?: number;
  distractionCount?: number;
  onPress?: () => void;
}

export const RecentAlertCard: React.FC<RecentAlertCardProps> = ({
  openAlerts,
  fatigueCount,
  distractionCount,
  onPress,
}) => {
  const hasBreakdown = (fatigueCount !== undefined && fatigueCount > 0) || (distractionCount !== undefined && distractionCount > 0);

  return (
    <TouchableOpacity
      activeOpacity={0.7}
      onPress={onPress}
      style={styles.card}
      accessibilityRole="button"
      accessibilityLabel={`Recent Alert Count: ${openAlerts} open alerts`}
    >
      <View style={styles.iconContainer}>
        <Bell size={18} color="#EA580C" strokeWidth={2.2} />
      </View>

      <View style={styles.textContainer}>
        <Text style={styles.title}>Recent Alert Count</Text>
        <Text style={styles.subtitle}>
          <Text style={styles.alertCount}>{openAlerts} </Text>
          open alerts
          {hasBreakdown && (
            <Text style={styles.breakdownText}>
              {' '}({fatigueCount ? `${fatigueCount} Fatigue` : ''}{fatigueCount && distractionCount ? ', ' : ''}{distractionCount ? `${distractionCount} Inattentive` : ''})
            </Text>
          )}
        </Text>
      </View>

      <ChevronRight size={18} color="#94A3B8" />
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 12,
    marginVertical: 8,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#F1F5F9',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 2,
  },
  iconContainer: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: '#FFF7ED',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  textContainer: {
    flex: 1,
  },
  title: {
    fontSize: 13,
    fontWeight: '600',
    color: '#0F172A',
  },
  subtitle: {
    fontSize: 12,
    color: '#64748B',
    marginTop: 2,
  },
  alertCount: {
    color: '#DC2626',
    fontWeight: '700',
  },
  breakdownText: {
    color: '#475569',
    fontWeight: '500',
    fontSize: 11,
  },
});
