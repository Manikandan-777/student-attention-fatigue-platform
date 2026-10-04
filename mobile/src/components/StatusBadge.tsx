import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { THEME, STATUS_MAPPING } from '../theme';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'base';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'base' }) => {
  const normalizedKey = (status in STATUS_MAPPING ? status : 'Unknown') as keyof typeof STATUS_MAPPING;
  const config = STATUS_MAPPING[normalizedKey];

  const isSmall = size === 'sm';
  const paddingH = isSmall ? THEME.spacing.space3 : THEME.spacing.space6;
  const paddingV = isSmall ? THEME.spacing.space1 : THEME.spacing.space2;
  const fontSize = isSmall ? THEME.typography.sizes.xs : THEME.typography.sizes.sm;

  return (
    <View
      accessibilityRole="text"
      accessibilityLabel={`Status: ${config.text}`}
      style={[
        styles.badge,
        {
          backgroundColor: config.bgColor,
          borderColor: config.borderColor,
          paddingHorizontal: paddingH,
          paddingVertical: paddingV,
        },
      ]}
    >
      <Text
        style={[
          styles.text,
          {
            color: config.textColor,
            fontSize,
          },
        ]}
      >
        {config.text}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    borderWidth: 1,
    borderRadius: THEME.radius.pill,
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {
    fontWeight: '600',
  },
});
