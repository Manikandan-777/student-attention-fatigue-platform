import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator } from 'react-native';
import {
  AlertTriangle,
  AlertOctagon,
  EyeOff,
  CheckCircle2,
  Eye,
  Clock,
  User,
  Volume2,
} from 'lucide-react-native';
import { Alert, AlertStatus } from '../types';
import { soundAlertService } from '../services/soundAlert';

interface StudentBehaviorAlertCardProps {
  alert: Alert;
  onUpdateStatus?: (alertId: number, nextStatus: AlertStatus) => Promise<void>;
  isUpdating?: boolean;
}

export const StudentBehaviorAlertCard: React.FC<StudentBehaviorAlertCardProps> = ({
  alert,
  onUpdateStatus,
  isUpdating = false,
}) => {
  const isFatigue = alert.type === 'fatigue';
  const isDistraction = alert.type === 'distraction';

  const formatTime = (isoString?: string | null) => {
    if (!isoString) return 'Just now';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoString;
    }
  };

  const getBehaviorTheme = () => {
    if (isFatigue) {
      return {
        badgeBg: '#FEE2E2',
        badgeText: '#DC2626',
        badgeBorder: '#FECACA',
        label: 'Fatigue Alert',
        sublabel: 'Drowsiness / Yawning',
        cardBorder: '#FCA5A5',
        iconBg: '#FEE2E2',
        iconColor: '#DC2626',
        Icon: AlertOctagon,
      };
    }
    if (isDistraction) {
      return {
        badgeBg: '#FEF3C7',
        badgeText: '#B45309',
        badgeBorder: '#FDE68A',
        label: 'Inattentive',
        sublabel: 'Looking Away / Off-Task',
        cardBorder: '#FCD34D',
        iconBg: '#FEF3C7',
        iconColor: '#D97706',
        Icon: EyeOff,
      };
    }
    return {
      badgeBg: '#F1F5F9',
      badgeText: '#475569',
      badgeBorder: '#E2E8F0',
      label: alert.type.replace('_', ' '),
      sublabel: 'System Notification',
      cardBorder: '#CBD5E1',
      iconBg: '#F1F5F9',
      iconColor: '#64748B',
      Icon: AlertTriangle,
    };
  };

  const theme = getBehaviorTheme();
  const IconComponent = theme.Icon;
  const studentLabel = alert.label ? (alert.label.startsWith('S') ? `Student ${alert.label}` : alert.label) : `Student #${alert.track_id ?? 'Unknown'}`;

  return (
    <View
      style={[
        styles.card,
        alert.status === 'Resolved' && styles.cardResolved,
      ]}
      accessibilityRole="alert"
      accessibilityLabel={`${theme.label} for ${studentLabel}: ${alert.message}. Status: ${alert.status}`}
    >
      {/* Top Header Row */}
      <View style={styles.headerRow}>
        <View style={styles.studentInfoGroup}>
          <View style={[styles.iconCircle, { backgroundColor: theme.iconBg }]}>
            <IconComponent size={18} color={theme.iconColor} strokeWidth={2.4} />
          </View>
          <View>
            <View style={styles.studentLabelRow}>
              <User size={13} color="#475569" style={styles.userIcon} />
              <Text style={styles.studentName}>{studentLabel}</Text>
            </View>
            <Text style={styles.behaviorSublabel}>{theme.sublabel}</Text>
          </View>
        </View>

        {/* Behavior and Status Badges */}
        <View style={styles.badgeContainer}>
          <View
            style={[
              styles.badge,
              { backgroundColor: theme.badgeBg, borderColor: theme.badgeBorder },
            ]}
          >
            <Text style={[styles.badgeText, { color: theme.badgeText }]}>
              {theme.label}
            </Text>
          </View>

          <View
            style={[
              styles.statusBadge,
              alert.status === 'Resolved'
                ? styles.statusResolved
                : alert.status === 'Viewed'
                ? styles.statusViewed
                : styles.statusNew,
            ]}
          >
            <Text
              style={[
                styles.statusBadgeText,
                alert.status === 'Resolved'
                  ? styles.statusResolvedText
                  : alert.status === 'Viewed'
                  ? styles.statusViewedText
                  : styles.statusNewText,
              ]}
            >
              {alert.status}
            </Text>
          </View>
        </View>
      </View>

      {/* Observation Message */}
      <Text style={styles.messageText}>{alert.message}</Text>

      {/* Footer Info & Actions */}
      <View style={styles.footerRow}>
        <View style={styles.metaRow}>
          <View style={styles.metaItem}>
            <Clock size={12} color="#94A3B8" />
            <Text style={styles.metaText}>{formatTime(alert.created_at)}</Text>
          </View>
          {alert.confidence !== undefined && (
            <View style={styles.metaItem}>
              <Text style={styles.metaConfidence}>
                {Math.round(alert.confidence * 100)}% conf
              </Text>
            </View>
          )}
        </View>

        {/* Action Buttons */}
        <View style={styles.actionsRow}>
          {/* Play Sound & Voice Alert */}
          <TouchableOpacity
            style={styles.soundPlayBtn}
            onPress={() => soundAlertService.triggerAlert(alert)}
            activeOpacity={0.7}
            accessibilityLabel={`Play sound alert for ${studentLabel}`}
          >
            <Volume2 size={13} color="#4F46E5" />
          </TouchableOpacity>

          {onUpdateStatus && alert.status !== 'Resolved' && (
            <>
              {alert.status === 'New' && (
                <TouchableOpacity
                  style={styles.viewedBtn}
                  disabled={isUpdating}
                  onPress={() => onUpdateStatus(alert.id, 'Viewed')}
                  activeOpacity={0.7}
                  accessibilityLabel={`Mark ${studentLabel} alert viewed`}
                >
                {isUpdating ? (
                  <ActivityIndicator size="small" color="#475569" />
                ) : (
                  <>
                    <Eye size={13} color="#475569" />
                    <Text style={styles.viewedBtnText}>View</Text>
                  </>
                )}
              </TouchableOpacity>
            )}

            <TouchableOpacity
              style={styles.resolveBtn}
              disabled={isUpdating}
              onPress={() => onUpdateStatus(alert.id, 'Resolved')}
              activeOpacity={0.7}
              accessibilityLabel={`Resolve ${studentLabel} alert`}
            >
              {isUpdating ? (
                <ActivityIndicator size="small" color="#16A34A" />
              ) : (
                <>
                  <CheckCircle2 size={13} color="#16A34A" />
                  <Text style={styles.resolveBtnText}>Resolve</Text>
                </>
              )}
            </TouchableOpacity>
          </>
        )}
      </View>

        {alert.status === 'Resolved' && (
          <View style={styles.resolvedConfirmed}>
            <CheckCircle2 size={14} color="#16A34A" />
            <Text style={styles.resolvedConfirmedText}>Resolved</Text>
          </View>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 14,
    marginVertical: 6,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
  },
  cardResolved: {
    backgroundColor: '#F8FAFC',
    borderColor: '#E2E8F0',
    opacity: 0.85,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  studentInfoGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  iconCircle: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  studentLabelRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  userIcon: {
    marginRight: 4,
  },
  studentName: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0F172A',
  },
  behaviorSublabel: {
    fontSize: 11,
    color: '#64748B',
    marginTop: 1,
  },
  badgeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  badge: {
    paddingHorizontal: 7,
    paddingVertical: 3,
    borderRadius: 6,
    borderWidth: 1,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '700',
  },
  statusBadge: {
    paddingHorizontal: 7,
    paddingVertical: 3,
    borderRadius: 6,
  },
  statusNew: {
    backgroundColor: '#EFF6FF',
  },
  statusNewText: {
    color: '#2563EB',
    fontSize: 11,
    fontWeight: '700',
  },
  statusViewed: {
    backgroundColor: '#FEF3C7',
  },
  statusViewedText: {
    color: '#D97706',
    fontSize: 11,
    fontWeight: '700',
  },
  statusResolved: {
    backgroundColor: '#DCFCE7',
  },
  statusResolvedText: {
    color: '#16A34A',
    fontSize: 11,
    fontWeight: '700',
  },
  messageText: {
    fontSize: 13,
    color: '#334155',
    lineHeight: 18,
    marginVertical: 6,
  },
  footerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 6,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#F1F5F9',
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  metaText: {
    fontSize: 11,
    color: '#94A3B8',
  },
  metaConfidence: {
    fontSize: 11,
    color: '#64748B',
    fontWeight: '600',
    backgroundColor: '#F1F5F9',
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 4,
  },
  actionsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  soundPlayBtn: {
    width: 26,
    height: 26,
    borderRadius: 6,
    backgroundColor: '#EEF2FF',
    borderWidth: 1,
    borderColor: '#C7D2FE',
    alignItems: 'center',
    justifyContent: 'center',
  },
  viewedBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderRadius: 6,
    backgroundColor: '#F1F5F9',
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  viewedBtnText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#475569',
  },
  resolveBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderRadius: 6,
    backgroundColor: '#F0FDF4',
    borderWidth: 1,
    borderColor: '#BBF7D0',
  },
  resolveBtnText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#16A34A',
  },
  resolvedConfirmed: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  resolvedConfirmedText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#16A34A',
  },
});
