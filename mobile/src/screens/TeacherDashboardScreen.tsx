import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { THEME } from '../theme';
import { ApiService } from '../services/api';
import { mobileTelemetry } from '../services/websocket';
import { OfflineBanner } from '../components/OfflineBanner';
import { AdvisoryBanner } from '../components/AdvisoryBanner';
import { ClassSnapshot } from '../types';

interface TeacherDashboardScreenProps {
  onNavigate: (screen: string, params?: Record<string, unknown>) => void;
}

export const TeacherDashboardScreen: React.FC<TeacherDashboardScreenProps> = ({
  onNavigate,
}) => {
  const [snapshot, setSnapshot] = useState<ClassSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [aiOffline, setAiOffline] = useState(false);
  const [cameraOffline, setCameraOffline] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const loadInitialData = async () => {
      try {
        const data = await ApiService.getTeacherDashboard();
        if (isMounted) setSnapshot(data);
      } catch {
        // Fallback to latest available
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadInitialData();

    // Register for high-priority loud push notifications (§8.3)
    import('../services/notifications')
      .then((m) => m.registerForPush())
      .catch(() => {});

    // Connect to WebSocket telemetry
    mobileTelemetry.connect();

    const unsubTel = mobileTelemetry.onTelemetry((data) => {
      if (data.snapshot && isMounted) {
        setSnapshot(data.snapshot);
      }
    });

    const unsubConn = mobileTelemetry.onConnectionChange((connected) => {
      if (isMounted) setIsWsConnected(connected);
    });

    const unsubSys = mobileTelemetry.onSystemStatus((status) => {
      if (isMounted) {
        setAiOffline(status.ai_server === 'Offline');
        setCameraOffline(status.cameras?.some((c) => c.state === 'Offline') ?? false);
      }
    });

    return () => {
      isMounted = false;
      unsubTel();
      unsubConn();
      unsubSys();
    };
  }, []);

  const counts = snapshot?.counts ?? {
    attentive: 0,
    distracted: 0,
    fatigued: 0,
    unknown: 0,
  };

  return (
    <ScrollView style={styles.container}>
      <OfflineBanner
        isNetworkOffline={!isWsConnected}
        isAiOffline={aiOffline}
        isCameraOffline={cameraOffline}
      />

      <View style={styles.content}>
        <Text style={styles.greeting}>Good Morning, Teacher</Text>

        <AdvisoryBanner
          advisory={snapshot?.fatigue_advisory}
          isOffline={!isWsConnected}
          isStale={aiOffline || cameraOffline}
        />

        <View style={styles.sessionCard}>
          <Text style={styles.sessionHeader}>Current Session</Text>
          <Text style={styles.className}>
            Class: {snapshot?.class_name ?? 'III AI & DS'}
          </Text>
          <View style={styles.statusRow}>
            <View style={styles.statusDot} />
            <Text style={styles.statusText}>
              Status: {snapshot?.status ?? 'Monitoring'}
            </Text>
          </View>

          <View style={styles.divider} />

          <Text style={styles.studentsCount}>
            Students: {snapshot?.students_detected ?? 0}
          </Text>

          <View style={styles.metricRow}>
            <Text style={styles.metricLabel}>Attentive</Text>
            <Text style={[styles.metricValue, { color: THEME.colors.accentSuccess }]}>
              {counts.attentive}
            </Text>
          </View>

          <View style={styles.metricRow}>
            <Text style={styles.metricLabel}>Distracted</Text>
            <Text style={[styles.metricValue, { color: THEME.colors.accentPrimary }]}>
              {counts.distracted}
            </Text>
          </View>

          <View style={styles.metricRow}>
            <Text style={styles.metricLabel}>Fatigue</Text>
            <Text style={[styles.metricValue, { color: THEME.colors.accentDanger }]}>
              {counts.fatigued}
            </Text>
          </View>

          <View style={styles.divider} />

          <TouchableOpacity
            style={styles.actionButton}
            onPress={() => onNavigate('Students')}
            accessibilityRole="button"
            accessibilityLabel="View Students"
          >
            <Text style={styles.actionButtonText}>[ View Students ]</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionButton}
            onPress={() => onNavigate('Alerts')}
            accessibilityRole="button"
            accessibilityLabel="View Alerts"
          >
            <Text style={styles.actionButtonText}>
              [ View Alerts {snapshot?.open_alerts ? `(${snapshot.open_alerts})` : ''} ]
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionButton}
            onPress={() => onNavigate('Reports')}
            accessibilityRole="button"
            accessibilityLabel="View Report"
          >
            <Text style={styles.actionButtonText}>[ View Report ]</Text>
          </TouchableOpacity>
        </View>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME.colors.bgApp,
  },
  content: {
    padding: THEME.spacing.space8,
  },
  greeting: {
    fontSize: THEME.typography.sizes.lg,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
    marginBottom: THEME.spacing.space6,
  },
  sessionCard: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    borderRadius: THEME.radius.xl,
    padding: THEME.spacing.space8,
  },
  sessionHeader: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.textSecondary,
    marginBottom: THEME.spacing.space2,
  },
  className: {
    fontSize: THEME.typography.sizes.base,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
    marginBottom: THEME.spacing.space2,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: THEME.spacing.space4,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: THEME.radius.pill,
    backgroundColor: THEME.colors.accentSuccess,
    marginRight: THEME.spacing.space2,
  },
  statusText: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.accentSuccess,
    fontWeight: '600',
  },
  divider: {
    height: 1,
    backgroundColor: THEME.colors.borderSubtle,
    marginVertical: THEME.spacing.space4,
  },
  studentsCount: {
    fontSize: THEME.typography.sizes.base,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
    marginBottom: THEME.spacing.space4,
  },
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: THEME.spacing.space2,
  },
  metricLabel: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.textBody,
  },
  metricValue: {
    fontSize: THEME.typography.sizes.sm,
    fontWeight: 'bold',
  },
  actionButton: {
    minHeight: THEME.spacing.space11, // 44dp minimum touch target
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: THEME.spacing.space2,
  },
  actionButtonText: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.accentPrimary,
    fontWeight: 'bold',
  },
});
