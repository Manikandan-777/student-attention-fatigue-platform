import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { THEME } from '../theme';
import { StatusBadge } from '../components/StatusBadge';
import { OfflineBanner } from '../components/OfflineBanner';
import { ApiService } from '../services/api';
import { SystemStatus } from '../types';

export const SystemStatusScreen: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    const loadStatus = async () => {
      try {
        const data = await ApiService.getSystemStatus();
        setStatus(data);
      } catch {
        // Fallback status for simulation
        setStatus({
          ai_server: 'Online',
          database: 'Online',
          api: 'Online',
          cameras: [
            { id: 'CAM-001', state: 'Online' },
            { id: 'CAM-002', state: 'Online' },
            { id: 'CAM-003', state: 'Offline' },
          ],
          fps: 22.4,
          model_mode: 'heuristic',
          privacy_mode: true,
        });
      }
    };

    loadStatus();
  }, []);

  const aiOffline = status?.ai_server === 'Offline';
  const cameraOffline = status?.cameras?.some((c) => c.state === 'Offline') ?? false;

  return (
    <ScrollView style={styles.container}>
      <OfflineBanner
        isAiOffline={aiOffline}
        isCameraOffline={cameraOffline}
      />

      <View style={styles.content}>
        <Text style={styles.header}>System Status</Text>

        {/* Infrastructure health per APP-21 */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Infrastructure Health</Text>
          <View style={styles.divider} />

          <View style={styles.statusRow}>
            <Text style={styles.serviceName}>AI Server</Text>
            <StatusBadge status={status?.ai_server ?? 'Online'} size="sm" />
          </View>

          <View style={styles.statusRow}>
            <Text style={styles.serviceName}>Database</Text>
            <StatusBadge status={status?.database ?? 'Online'} size="sm" />
          </View>

          <View style={styles.statusRow}>
            <Text style={styles.serviceName}>API</Text>
            <StatusBadge status={status?.api ?? 'Online'} size="sm" />
          </View>
        </View>

        {/* Camera status per APP-20 */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Camera Status</Text>
          <View style={styles.divider} />

          {status?.cameras?.map((cam) => (
            <View key={cam.id} style={styles.statusRow}>
              <Text style={styles.serviceName}>{cam.id}</Text>
              <StatusBadge status={cam.state} size="sm" />
            </View>
          ))}
        </View>

        {/* Telemetry info */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Configuration</Text>
          <View style={styles.divider} />

          <View style={styles.statusRow}>
            <Text style={styles.serviceName}>Target FPS</Text>
            <Text style={styles.configVal}>{status?.fps ?? 20.0}</Text>
          </View>

          <View style={styles.statusRow}>
            <Text style={styles.serviceName}>Model Mode</Text>
            <Text style={styles.configVal}>
              {(status?.model_mode ?? 'heuristic').toUpperCase()}
            </Text>
          </View>

          <View style={styles.statusRow}>
            <Text style={styles.serviceName}>Privacy Mode</Text>
            <Text style={styles.configVal}>
              {status?.privacy_mode ? 'Enabled (No Video)' : 'Disabled'}
            </Text>
          </View>
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
  header: {
    fontSize: THEME.typography.sizes.lg,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
    marginBottom: THEME.spacing.space6,
  },
  card: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    borderRadius: THEME.radius.xl,
    padding: THEME.spacing.space8,
    marginBottom: THEME.spacing.space6,
  },
  cardTitle: {
    fontSize: THEME.typography.sizes.base,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
  },
  divider: {
    height: 1,
    backgroundColor: THEME.colors.borderSubtle,
    marginVertical: THEME.spacing.space4,
  },
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: THEME.spacing.space2,
  },
  serviceName: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.textBody,
  },
  configVal: {
    fontSize: THEME.typography.sizes.sm,
    fontWeight: '600',
    color: THEME.colors.textPrimary,
  },
});
