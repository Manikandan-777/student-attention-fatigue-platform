import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'base';
  prefixDot?: boolean;
  prefixPlus?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'base',
  prefixDot = false,
  prefixPlus = false,
}) => {
  const norm = status.toLowerCase();

  let bg = '#F1F5F9';
  let color = '#475569';
  let borderColor = 'transparent';

  if (norm === 'active' || norm === 'attentive' || norm === 'normal') {
    bg = '#DCFCE7';
    color = '#15803D';
  } else if (norm === 'live') {
    bg = '#DCFCE7';
    color = '#15803D';
  } else if (norm === 'inactive') {
    bg = '#F1F5F9';
    color = '#64748B';
  } else if (norm === 'teacher' || norm === 'admin') {
    bg = '#EEF2FF';
    color = '#4F46E5';
  } else if (norm === 'distracted') {
    bg = '#FEF3C7';
    color = '#D97706';
  } else if (norm === 'fatigued') {
    bg = '#FEE2E2';
    color = '#DC2626';
  }

  const isSmall = size === 'sm';

  return (
    <View
      accessibilityRole="text"
      accessibilityLabel={`Status: ${status}`}
      style={[
        styles.badge,
        {
          backgroundColor: bg,
          borderColor,
          paddingHorizontal: isSmall ? 8 : 10,
          paddingVertical: isSmall ? 3 : 5,
        },
      ]}
    >
      {prefixDot && <Text style={[styles.dot, { color }]}>● </Text>}
      {prefixPlus && <Text style={[styles.plus, { color }]}>+ </Text>}
      <Text
        style={[
          styles.text,
          {
            color,
            fontSize: isSmall ? 11 : 12,
          },
        ]}
      >
        {status}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    borderRadius: 9999,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  dot: {
    fontSize: 8,
    marginRight: 2,
    fontWeight: 'bold',
  },
  plus: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  text: {
    fontWeight: '600',
  },
});
