import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { CheckCircle2, MessageCircle, AlertTriangle, AlertOctagon, ChevronRight, HelpCircle } from 'lucide-react-native';
import { THEME } from '../theme';
import { FatigueAdvisory } from '../types';

interface AdvisoryBannerProps {
  advisory?: FatigueAdvisory | null;
  fatiguePct?: number | null;
  isOffline?: boolean;
  onPress?: () => void;
}

export function getFatigueMessage(pct: number): { level: 1 | 2 | 3 | 4; text: string } {
  if (pct < 25) return { level: 1, text: 'Continue with the class.' };
  if (pct < 50) return { level: 2, text: 'Make the session more interactive.' };
  if (pct < 75) return { level: 3, text: 'Do a short activity or give a short break.' };
  return { level: 4, text: 'Most students show fatigue indicators. Consider continuing the class tomorrow.' };
}

export const AdvisoryBanner: React.FC<AdvisoryBannerProps> = ({
  advisory,
  fatiguePct,
  isOffline = false,
  onPress,
}) => {
  // If offline
  if (isOffline) {
    return (
      <View style={[styles.container, styles.offlineContainer]}>
        <View style={[styles.iconCircle, { backgroundColor: '#F1F5F9' }]}>
          <HelpCircle size={18} color="#64748B" />
        </View>
        <View style={styles.textContainer}>
          <Text style={styles.title}>Realtime telemetry disconnected</Text>
          <Text style={styles.subtitle}>Showing latest available advisory</Text>
        </View>
      </View>
    );
  }

  // Determine score & level
  const effectivePct = advisory?.class_fatigue_pct ?? fatiguePct;

  if (effectivePct === undefined || effectivePct === null) {
    return (
      <View style={[styles.container, styles.emptyContainer]}>
        <View style={[styles.iconCircle, { backgroundColor: '#F1F5F9' }]}>
          <HelpCircle size={18} color="#64748B" />
        </View>
        <View style={styles.textContainer}>
          <Text style={styles.title}>Not enough data</Text>
          <Text style={styles.subtitle}>Observing classroom to compute fatigue advisory</Text>
        </View>
      </View>
    );
  }

  const { level, text } = advisory?.message
    ? { level: advisory.level, text: advisory.message }
    : getFatigueMessage(effectivePct);

  const roundedPct = Math.round(effectivePct);

  const getLevelStyle = () => {
    switch (level) {
      case 1:
        return {
          bg: '#F0FDF4',
          border: '#BBF7D0',
          iconBg: '#DCFCE7',
          iconColor: '#16A34A',
          Icon: CheckCircle2,
        };
      case 2:
        return {
          bg: '#FEF3C7',
          border: '#FDE68A',
          iconBg: '#FCD34D',
          iconColor: '#B45309',
          Icon: MessageCircle,
        };
      case 3:
        return {
          bg: '#FEF3C7',
          border: '#FCD34D',
          iconBg: '#F59E0B',
          iconColor: '#FFFFFF',
          Icon: AlertTriangle,
        };
      case 4:
      default:
        return {
          bg: '#FEE2E2',
          border: '#FECACA',
          iconBg: '#EF4444',
          iconColor: '#FFFFFF',
          Icon: AlertOctagon,
        };
    }
  };

  const styleConfig = getLevelStyle();
  const IconComponent = styleConfig.Icon;

  return (
    <TouchableOpacity
      activeOpacity={onPress ? 0.7 : 1}
      onPress={onPress}
      style={[
        styles.container,
        {
          backgroundColor: styleConfig.bg,
          borderColor: styleConfig.border,
        },
      ]}
      accessibilityRole="alert"
      accessibilityLabel={`Advisory Level ${level}: ${text}. Class fatigue score is ${roundedPct}%.`}
    >
      <View style={[styles.iconCircle, { backgroundColor: styleConfig.iconBg }]}>
        <IconComponent size={18} color={styleConfig.iconColor} strokeWidth={2.4} />
      </View>

      <View style={styles.textContainer}>
        <View style={styles.titleRow}>
          <Text style={styles.title} numberOfLines={2}>
            {text}
          </Text>
        </View>
        <Text style={styles.subtitle}>
          Class fatigue score is {roundedPct}%.
        </Text>
      </View>

      <ChevronRight size={18} color="#94A3B8" style={styles.chevron} />
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 14,
    borderWidth: 1,
    paddingVertical: 12,
    paddingHorizontal: 12,
    marginVertical: 10,
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 2,
  },
  iconCircle: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  textContainer: {
    flex: 1,
    paddingRight: 4,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  title: {
    fontSize: 13,
    fontWeight: '700',
    color: '#0F172A',
    lineHeight: 18,
  },
  subtitle: {
    fontSize: 11,
    color: '#64748B',
    marginTop: 2,
    fontWeight: '500',
  },
  chevron: {
    marginLeft: 6,
  },
  emptyContainer: {
    backgroundColor: '#F8FAFC',
    borderColor: '#E2E8F0',
  },
  offlineContainer: {
    backgroundColor: '#F8FAFC',
    borderColor: '#CBD5E1',
  },
});
