import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { THEME } from '../theme';

interface OfflineBannerProps {
  isNetworkOffline?: boolean;
  isAiOffline?: boolean;
  isCameraOffline?: boolean;
}

export const OfflineBanner: React.FC<OfflineBannerProps> = ({
  isNetworkOffline = false,
  isAiOffline = false,
  isCameraOffline = false,
}) => {
  if (!isNetworkOffline && !isAiOffline && !isCameraOffline) {
    return null;
  }

  const items: { title: string; message: string }[] = [];

  if (isNetworkOffline) {
    items.push({
      title: 'No Internet Connection',
      message: 'Showing the latest available data.',
    });
  }
  if (isAiOffline) {
    items.push({
      title: '⚠ AI Service Unavailable',
      message: 'New predictions are currently unavailable.',
    });
  }
  if (isCameraOffline) {
    items.push({
      title: '⚠ Camera Offline',
      message:
        'The classroom camera is currently unavailable.\n\nAI monitoring has been paused.',
    });
  }

  return (
    <View>
      {items.map((item, idx) => (
        <View
          key={idx}
          accessibilityRole="alert"
          accessibilityLiveRegion="polite"
          style={styles.banner}
        >
          <Text style={styles.title}>{item.title}</Text>
          <Text style={styles.message}>{item.message}</Text>
        </View>
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  banner: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.accentDanger,
    borderWidth: 1,
    borderRadius: THEME.radius.lg,
    padding: THEME.spacing.space8,
    marginVertical: THEME.spacing.space6,
    marginHorizontal: THEME.spacing.space8,
  },
  title: {
    color: THEME.colors.accentDanger,
    fontSize: THEME.typography.sizes.sm,
    fontWeight: 'bold',
    marginBottom: THEME.spacing.space2,
  },
  message: {
    color: THEME.colors.textBody,
    fontSize: THEME.typography.sizes.xs,
    lineHeight: THEME.typography.lineHeights.xs,
  },
});
