import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { THEME } from '../theme';
import { FatigueAdvisory } from '../types';

interface AdvisoryBannerProps {
  advisory?: FatigueAdvisory | null;
  isOffline?: boolean;
  isStale?: boolean;
}

const LEVEL_STYLE = {
  1: {
    icon: '✓',
    color: THEME.colors.accentSuccess,
    bg: THEME.colors.bgSuccess,
    border: THEME.colors.accentSuccess,
    tag: 'CONTINUE',
  },
  2: {
    icon: '💬',
    color: THEME.colors.accentPrimary,
    bg: THEME.colors.bgInfo,
    border: THEME.colors.accentPrimary,
    tag: 'INTERACTIVE',
  },
  3: {
    icon: '⚠',
    color: THEME.colors.accentDanger,
    bg: THEME.colors.bgSurface,
    border: THEME.colors.accentDanger,
    tag: 'SHORT_BREAK',
  },
  4: {
    icon: '🛑',
    color: THEME.colors.accentDanger,
    bg: THEME.colors.bgSurface,
    border: THEME.colors.accentDanger,
    tag: 'RESCHEDULE',
  },
} as const;

export const AdvisoryBanner: React.FC<AdvisoryBannerProps> = ({
  advisory,
  isOffline = false,
  isStale = false,
}) => {
  // If connection is offline, mark advisory as Stale or do not show false live state
  if (isOffline) {
    return (
      <View
        accessibilityRole="alert"
        accessibilityLiveRegion="polite"
        style={[styles.banner, styles.staleBanner]}
      >
        <Text style={styles.staleTitle}>[Stale Advisory]</Text>
        <Text style={styles.staleMessage}>
          Live classroom telemetry disconnected. Advisory is currently paused.
        </Text>
      </View>
    );
  }

  // If advisory is null / not enough data (fewer than 5 usable tracks)
  if (!advisory) {
    return (
      <View
        accessibilityRole="alert"
        accessibilityLiveRegion="polite"
        style={[styles.banner, styles.noDataBanner]}
      >
        <View style={styles.headerRow}>
          <Text style={styles.noDataIcon}>?</Text>
          <Text style={styles.noDataTitle}>Not enough data</Text>
        </View>
        <Text style={styles.noDataMessage}>
          Awaiting at least 5 usable student tracks to compute class fatigue advisory.
        </Text>
      </View>
    );
  }

  const styleConfig = LEVEL_STYLE[advisory.level] || LEVEL_STYLE[1];
  const pctRounded = Math.round(advisory.class_fatigue_pct);

  return (
    <View
      role="alert"
      accessibilityRole="alert"
      accessibilityLiveRegion="polite"
      style={[
        styles.banner,
        {
          backgroundColor: styleConfig.bg,
          borderColor: styleConfig.border,
        },
      ]}
    >
      <View style={styles.headerRow}>
        <Text style={[styles.levelIcon, { color: styleConfig.color }]}>
          {styleConfig.icon}
        </Text>
        <Text style={[styles.levelLabel, { color: styleConfig.color }]}>
          Level {advisory.level}: {styleConfig.tag}
        </Text>
        {isStale && <Text style={styles.staleTag}>(Stale)</Text>}
      </View>

      <Text style={styles.advisoryMessage}>{advisory.message}</Text>

      <View style={styles.footerRow}>
        <Text style={styles.scoreText}>
          {pctRounded}% fatigue indicators ({advisory.usable_tracks} students observed)
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  banner: {
    borderWidth: 1,
    borderRadius: THEME.radius.xl,
    padding: THEME.spacing.space8,
    marginVertical: THEME.spacing.space4,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: THEME.spacing.space2,
  },
  levelIcon: {
    fontSize: THEME.typography.sizes.base,
    fontWeight: 'bold',
    marginRight: THEME.spacing.space4,
  },
  levelLabel: {
    fontSize: THEME.typography.sizes.sm,
    fontWeight: 'bold',
    textTransform: 'uppercase',
  },
  advisoryMessage: {
    fontSize: THEME.typography.sizes.sm,
    lineHeight: THEME.typography.lineHeights.sm,
    color: THEME.colors.textPrimary,
    fontWeight: '600',
    marginBottom: THEME.spacing.space4,
  },
  footerRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  scoreText: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textSecondary,
  },
  staleTag: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textMuted,
    marginLeft: THEME.spacing.space4,
    fontStyle: 'italic',
  },
  staleBanner: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
  },
  staleTitle: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textSecondary,
    fontWeight: 'bold',
    marginBottom: THEME.spacing.space1,
  },
  staleMessage: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textMuted,
  },
  noDataBanner: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
  },
  noDataIcon: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.textSecondary,
    fontWeight: 'bold',
    marginRight: THEME.spacing.space4,
  },
  noDataTitle: {
    fontSize: THEME.typography.sizes.xs,
    fontWeight: 'bold',
    color: THEME.colors.textSecondary,
    textTransform: 'uppercase',
  },
  noDataMessage: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textSecondary,
    marginTop: THEME.spacing.space1,
  },
});
