import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Users, CheckCircle2, EyeOff, AlertTriangle, Bell } from 'lucide-react-native';
import { THEME } from '../theme';

export type StatType = 'students' | 'attentive' | 'distracted' | 'fatigued' | 'alerts';

interface StatCardProps {
  type: StatType;
  label: string;
  value: number | string;
  subtext?: string;
  onPress?: () => void;
}

export const StatCard: React.FC<StatCardProps> = ({
  type,
  label,
  value,
  subtext,
  onPress,
}) => {
  const getStyleForType = () => {
    switch (type) {
      case 'students':
        return {
          iconBg: THEME.colors.students.bg,
          iconColor: THEME.colors.students.icon,
          Icon: Users,
        };
      case 'attentive':
        return {
          iconBg: THEME.colors.attentive.bg,
          iconColor: THEME.colors.attentive.icon,
          Icon: CheckCircle2,
        };
      case 'distracted':
        return {
          iconBg: THEME.colors.distracted.bg,
          iconColor: THEME.colors.distracted.icon,
          Icon: EyeOff,
        };
      case 'fatigued':
        return {
          iconBg: THEME.colors.fatigued.bg,
          iconColor: THEME.colors.fatigued.icon,
          Icon: AlertTriangle,
        };
      case 'alerts':
      default:
        return {
          iconBg: THEME.colors.alerts.bg,
          iconColor: THEME.colors.alerts.icon,
          Icon: Bell,
        };
    }
  };

  const { iconBg, iconColor, Icon } = getStyleForType();

  const content = (
    <View style={styles.card}>
      <View style={[styles.iconWrapper, { backgroundColor: iconBg }]}>
        <Icon size={16} color={iconColor} strokeWidth={2.2} />
      </View>
      <Text style={styles.value}>{value}</Text>
      <Text style={styles.label} numberOfLines={1}>{label}</Text>
      {subtext ? <Text style={styles.subtext}>{subtext}</Text> : null}
    </View>
  );

  if (onPress) {
    return (
      <TouchableOpacity
        onPress={onPress}
        activeOpacity={0.7}
        accessibilityRole="button"
        accessibilityLabel={`${label}: ${value}`}
        style={styles.touchable}
      >
        {content}
      </TouchableOpacity>
    );
  }

  return <View style={styles.touchable}>{content}</View>;
};

const styles = StyleSheet.create({
  touchable: {
    flex: 1,
    minWidth: 62,
    marginHorizontal: 3,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    paddingVertical: 10,
    paddingHorizontal: 4,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#F1F5F9',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
  },
  iconWrapper: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 6,
  },
  value: {
    fontSize: 16,
    fontWeight: '700',
    color: THEME.colors.textPrimary,
    lineHeight: 20,
  },
  label: {
    fontSize: 10,
    fontWeight: '500',
    color: THEME.colors.textSecondary,
    marginTop: 2,
    textAlign: 'center',
  },
  subtext: {
    fontSize: 9,
    color: THEME.colors.textMuted,
    marginTop: 1,
  },
});
