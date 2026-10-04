import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { THEME } from '../theme';
import { StatusBadge } from '../components/StatusBadge';
import { ApiService } from '../services/api';
import { mobileTelemetry } from '../services/websocket';
import { Alert, AlertStatus } from '../types';

export const AlertCenterScreen: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filter, setFilter] = useState<'All' | AlertStatus>('All');
  const [loading, setLoading] = useState(true);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const data = await ApiService.getAlerts();
      setAlerts(data);
    } catch {
      // offline / fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();

    const unsub = mobileTelemetry.onAlert((newAlert) => {
      setAlerts((prev) => {
        if (prev.some((a) => a.id === newAlert.id)) {
          return prev.map((a) => (a.id === newAlert.id ? newAlert : a));
        }
        return [newAlert, ...prev];
      });
    });

    return () => unsub();
  }, []);

  const handleUpdate = async (id: number, nextStatus: AlertStatus) => {
    try {
      const updated = await ApiService.updateAlertStatus(id, nextStatus);
      setAlerts((prev) => prev.map((a) => (a.id === id ? updated : a)));
    } catch {
      // update state optimistically
      setAlerts((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: nextStatus } : a))
      );
    }
  };

  const filteredAlerts = alerts
    .filter((a) => (filter === 'All' ? true : a.status === filter))
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Alert Center</Text>

      {/* Filter Tabs */}
      <View style={styles.tabRow}>
        {(['All', 'New', 'Viewed', 'Resolved'] as const).map((tab) => (
          <TouchableOpacity
            key={tab}
            onPress={() => setFilter(tab)}
            style={[
              styles.tabButton,
              filter === tab && styles.tabButtonActive,
            ]}
            accessibilityRole="button"
            accessibilityLabel={`Filter ${tab}`}
          >
            <Text
              style={[
                styles.tabText,
                filter === tab && styles.tabTextActive,
              ]}
            >
              {tab}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading ? (
        <ActivityIndicator color={THEME.colors.accentPrimary} style={styles.loader} />
      ) : filteredAlerts.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyTitle}>No alerts</Text>
          <Text style={styles.emptySubtitle}>
            {filter === 'All'
              ? 'All quiet! No active alerts reported for this session.'
              : `No alerts currently with status "${filter}".`}
          </Text>
        </View>
      ) : (
        <FlatList
          data={filteredAlerts}
          keyExtractor={(item) => item.id.toString()}
          renderItem={({ item }) => (
            <View style={styles.alertCard}>
              <View style={styles.alertHeader}>
                <Text style={styles.alertTitle}>
                  {item.label ? `⚠ Student ${item.label}` : '⚠ System Alert'}
                </Text>
                <StatusBadge status={item.status === 'Resolved' ? 'Attentive' : 'Fatigued'} size="sm" />
              </View>

              <Text style={styles.alertMessage}>{item.message}</Text>

              <Text style={styles.alertMeta}>
                Confidence: {Math.round(item.confidence * 100)}% | Time: {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </Text>

              <View style={styles.actionRow}>
                {item.status === 'New' && (
                  <TouchableOpacity
                    style={[styles.actionBtn, styles.viewedBtn]}
                    onPress={() => handleUpdate(item.id, 'Viewed')}
                    accessibilityRole="button"
                    accessibilityLabel={`Mark alert ${item.id} Viewed`}
                  >
                    <Text style={styles.viewedBtnText}>Mark Viewed</Text>
                  </TouchableOpacity>
                )}

                {item.status !== 'Resolved' && (
                  <TouchableOpacity
                    style={[styles.actionBtn, styles.resolveBtn]}
                    onPress={() => handleUpdate(item.id, 'Resolved')}
                    accessibilityRole="button"
                    accessibilityLabel={`Resolve alert ${item.id}`}
                  >
                    <Text style={styles.resolveBtnText}>Resolve</Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>
          )}
          contentContainerStyle={styles.listContent}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME.colors.bgApp,
    padding: THEME.spacing.space8,
  },
  header: {
    fontSize: THEME.typography.sizes.lg,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
    marginBottom: THEME.spacing.space6,
  },
  tabRow: {
    flexDirection: 'row',
    marginBottom: THEME.spacing.space6,
    backgroundColor: THEME.colors.bgSurface,
    borderRadius: THEME.radius.lg,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    padding: THEME.spacing.space1,
  },
  tabButton: {
    flex: 1,
    minHeight: THEME.spacing.space11, // 44dp
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: THEME.radius.md,
  },
  tabButtonActive: {
    backgroundColor: THEME.colors.accentPrimary,
  },
  tabText: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textSecondary,
    fontWeight: '600',
  },
  tabTextActive: {
    color: THEME.colors.bgSurface,
  },
  loader: {
    marginTop: THEME.spacing.space12,
  },
  listContent: {
    paddingBottom: THEME.spacing.space10,
  },
  emptyContainer: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    borderRadius: THEME.radius.xl,
    padding: THEME.spacing.space12,
    alignItems: 'center',
  },
  emptyTitle: {
    fontSize: THEME.typography.sizes.base,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
    marginBottom: THEME.spacing.space2,
  },
  emptySubtitle: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textSecondary,
    textAlign: 'center',
  },
  alertCard: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    borderRadius: THEME.radius.xl,
    padding: THEME.spacing.space8,
    marginBottom: THEME.spacing.space4,
  },
  alertHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: THEME.spacing.space2,
  },
  alertTitle: {
    fontSize: THEME.typography.sizes.sm,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
  },
  alertMessage: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.textBody,
    marginBottom: THEME.spacing.space4,
  },
  alertMeta: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textMuted,
    marginBottom: THEME.spacing.space4,
  },
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: THEME.spacing.space4,
  },
  actionBtn: {
    minHeight: THEME.spacing.space11, // 44dp
    paddingHorizontal: THEME.spacing.space6,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: THEME.radius.lg,
  },
  viewedBtn: {
    borderColor: THEME.colors.borderStrong,
    borderWidth: 1,
    backgroundColor: THEME.colors.bgSurface,
  },
  viewedBtnText: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textBody,
    fontWeight: '600',
  },
  resolveBtn: {
    backgroundColor: THEME.colors.bgSuccess,
    borderColor: THEME.colors.accentSuccess,
    borderWidth: 1,
  },
  resolveBtnText: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.accentSuccess,
    fontWeight: 'bold',
  },
});
