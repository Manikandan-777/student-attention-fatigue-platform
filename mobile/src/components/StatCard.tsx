import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { THEME } from '../theme';

interface StatCardProps {
  label: string;
  value: number | string;
  subtext?: string;
  onPress?: () => void;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  subtext,
  onPress,
}) => {
  const content = (
    <View style={styles.card}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value}</Text>
      {subtext && <Text style={styles.subtext}>{subtext}</Text>}
    </View>
  );

  if (onPress) {
    return (
      <TouchableOpacity
        onPress={onPress}
        activeOpacity={0.8}
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
    minHeight: THEME.spacing.space11, // Minimum 44dp touch target per UI-7
    marginBottom: THEME.spacing.space4,
  },
  card: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    borderRadius: THEME.radius.xl,
    padding: THEME.spacing.space8,
    justifyContent: 'center',
  },
  label: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.textSecondary,
    marginBottom: THEME.spacing.space1,
  },
  value: {
    fontSize: THEME.typography.sizes.xl,
    color: THEME.colors.textPrimary,
    fontWeight: 'bold',
  },
  subtext: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textMuted,
    marginTop: THEME.spacing.space1,
  },
});
