import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
  Modal,
} from 'react-native';
import { Menu, Bell, ChevronDown, Check } from 'lucide-react-native';
import { THEME } from '../theme';
import { ApiService } from '../services/api';
import { mobileTelemetry } from '../services/websocket';
import { StatCard } from '../components/StatCard';
import { AdvisoryBanner, getFatigueMessage } from '../components/AdvisoryBanner';
import { TrendLineChart } from '../components/TrendLineChart';
import { StatusSplitDonut } from '../components/StatusSplitDonut';
import { RecentAlertCard } from '../components/RecentAlertCard';
import { StudentBehaviorAlertsModal } from '../components/StudentBehaviorAlertsModal';
import { EmptySessionState } from '../components/EmptySessionState';
import { OfflineState } from '../components/OfflineState';
import { Alert, AlertStatus, ClassSnapshot, FatigueAdvisory, Session } from '../types';
import { soundAlertService, speechService } from '../services/soundAlert';

interface AdminDashboardScreenProps {
  onNavigateTab?: (tab: string) => void;
}

export const AdminDashboardScreen: React.FC<AdminDashboardScreenProps> = ({
  onNavigateTab,
}) => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [sessionModalVisible, setSessionModalVisible] = useState(false);

  const [snapshot, setSnapshot] = useState<ClassSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [isWsConnected, setIsWsConnected] = useState(false);

  // Live trend points (Attention & Fatigue)
  const [attPoints, setAttPoints] = useState<Array<{ ts: string; value: number }>>([]);
  const [fatPoints, setFatPoints] = useState<Array<{ ts: string; value: number }>>([]);

  // Hysteresis for fatigue advisory (STATUS_HYSTERESIS_S = 3s)
  const [confirmedAdvisory, setConfirmedAdvisory] = useState<FatigueAdvisory | null>(null);
  const candidateLevelRef = useRef<{ level: number; since: number; advisory: FatigueAdvisory } | null>(null);

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isAlertsModalVisible, setIsAlertsModalVisible] = useState(false);
  const [updatingAlertId, setUpdatingAlertId] = useState<number | null>(null);

  // Auto-Shout controls (30s periodic loop & immediate high fatigue emergency shout)
  const [autoShoutEnabled, setAutoShoutEnabled] = useState(true);
  const lastHighFatigueShoutRef = useRef<number>(0);
  const lastShoutTimeRef = useRef<number>(0);

  // Live references so background intervals/callbacks always read latest state without resetting timers
  const snapshotRef = useRef<ClassSnapshot | null>(snapshot);
  const confirmedAdvisoryRef = useRef<FatigueAdvisory | null>(confirmedAdvisory);
  const alertsRef = useRef<Alert[]>(alerts);
  const autoShoutEnabledRef = useRef<boolean>(autoShoutEnabled);

  useEffect(() => {
    snapshotRef.current = snapshot;
  }, [snapshot]);

  useEffect(() => {
    confirmedAdvisoryRef.current = confirmedAdvisory;
  }, [confirmedAdvisory]);

  useEffect(() => {
    alertsRef.current = alerts;
  }, [alerts]);

  useEffect(() => {
    autoShoutEnabledRef.current = autoShoutEnabled;
  }, [autoShoutEnabled]);

  const checkAndShoutHighFatigue = (snap: ClassSnapshot | null, adv?: FatigueAdvisory | null) => {
    if (!autoShoutEnabledRef.current || soundAlertService.getIsMuted() || !snap) return;
    const fatPct = adv?.class_fatigue_pct ?? snap.class_fatigue_pct ?? (snap.counts ? (snap.counts.fatigued / (snap.students_detected || 1)) * 100 : 0);
    const count = snap.counts?.fatigued ?? 0;
    const isHigh = fatPct >= 35 || count >= 3 || (adv?.level ?? 0) >= 2;
    const now = Date.now();

    if (isHigh && (now - lastHighFatigueShoutRef.current >= 18000)) {
      lastHighFatigueShoutRef.current = now;
      lastShoutTimeRef.current = now;
      soundAlertService.shoutImmediateHighFatigue({
        fatiguePct: fatPct,
        count: count,
        advisoryText: adv?.message || 'High student fatigue detected in session',
      });
    }
  };

  const fetchAlerts = async (sessionId?: number) => {
    try {
      const serverAlerts = await ApiService.getAlerts(sessionId);
      if (serverAlerts && serverAlerts.length > 0) {
        setAlerts(serverAlerts);
        alertsRef.current = serverAlerts;
      }
    } catch {
      // Ignore
    }
  };

  const loadSessions = async () => {
    try {
      const sessList = await ApiService.getSessions();
      const safeList = Array.isArray(sessList) ? sessList : [];
      setSessions(safeList);

      const activeSess = safeList.find((s) => s.status === 'Monitoring') || safeList[0];
      if (activeSess && (!selectedSessionId || !safeList.some((s) => s.id === selectedSessionId))) {
        setSelectedSessionId(activeSess.id);
        mobileTelemetry.subscribeSession(activeSess.id);
        fetchAlerts(activeSess.id);
      }
    } catch {
      // Keep previous
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    loadSessions();

    mobileTelemetry.connect(selectedSessionId || undefined);

    const unsubTel = mobileTelemetry.onTelemetry(({ snapshot: liveSnap, ts }) => {
      if (!isMounted || !liveSnap) return;

      setSnapshot(liveSnap);
      snapshotRef.current = liveSnap;

      const timeLabel = ts
        ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      if (liveSnap.avg_attention_score !== undefined) {
        setAttPoints((prev) => [...prev, { ts: timeLabel, value: liveSnap.avg_attention_score }].slice(-20));
      }

      const fatPct = liveSnap.fatigue_advisory?.class_fatigue_pct ?? liveSnap.class_fatigue_pct ?? 0;
      setFatPoints((prev) => [...prev, { ts: timeLabel, value: fatPct }].slice(-20));

      // IMMEDIATE SHOUT on high student fatigue detection
      checkAndShoutHighFatigue(liveSnap, liveSnap.fatigue_advisory);

      const rawLevel = liveSnap.fatigue_advisory?.level ?? getFatigueMessage(fatPct).level;

      if (confirmedAdvisoryRef.current && confirmedAdvisoryRef.current.level !== rawLevel) {
        if (candidateLevelRef.current?.level === rawLevel) {
          if (Date.now() - candidateLevelRef.current.since >= 3000) {
            const nextAdv = liveSnap.fatigue_advisory ?? {
              level: rawLevel,
              class_fatigue_pct: fatPct,
              code: 'SHORT_BREAK',
              message: getFatigueMessage(fatPct).text,
              usable_tracks: liveSnap.students_detected,
              since: new Date().toISOString(),
            };
            setConfirmedAdvisory(nextAdv);
            confirmedAdvisoryRef.current = nextAdv;
            candidateLevelRef.current = null;
          }
        } else {
          candidateLevelRef.current = {
            level: rawLevel,
            since: Date.now(),
            advisory: liveSnap.fatigue_advisory ?? {
              level: rawLevel,
              class_fatigue_pct: fatPct,
              code: 'SHORT_BREAK',
              message: getFatigueMessage(fatPct).text,
              usable_tracks: liveSnap.students_detected,
              since: new Date().toISOString(),
            },
          };
        }
      } else {
        candidateLevelRef.current = null;
        if (liveSnap.fatigue_advisory) {
          setConfirmedAdvisory(liveSnap.fatigue_advisory);
          confirmedAdvisoryRef.current = liveSnap.fatigue_advisory;
        }
      }
    });

    const unsubConn = mobileTelemetry.onConnectionChange((connected) => {
      if (isMounted) setIsWsConnected(connected);
    });

    const unsubAlert = mobileTelemetry.onAlert((newAlert) => {
      setAlerts((prev) => {
        const exists = prev.some((a) => a.id === newAlert.id);
        const updated = exists ? prev.map((a) => (a.id === newAlert.id ? newAlert : a)) : [newAlert, ...prev];
        alertsRef.current = updated;
        return updated;
      });

      // Immediate voice announcement for new incoming alert
      if (newAlert.status === 'New' && autoShoutEnabledRef.current && !soundAlertService.getIsMuted()) {
        const curFatPct = confirmedAdvisoryRef.current?.class_fatigue_pct ?? snapshotRef.current?.class_fatigue_pct ?? 0;
        if (newAlert.type === 'fatigue' && (newAlert.confidence >= 0.85 || curFatPct >= 35)) {
          soundAlertService.shoutImmediateHighFatigue({
            fatiguePct: curFatPct,
            count: snapshotRef.current?.counts?.fatigued ?? 0,
            studentLabel: newAlert.label ? `Student ${newAlert.label}` : undefined,
            advisoryText: newAlert.message,
          });
          lastHighFatigueShoutRef.current = Date.now();
          lastShoutTimeRef.current = Date.now();
        } else {
          soundAlertService.triggerAlert(newAlert);
          lastShoutTimeRef.current = Date.now();
        }
      }
    });

    return () => {
      isMounted = false;
      unsubTel();
      unsubConn();
      unsubAlert();
    };
  }, [selectedSessionId]);

  // AUTOMATIC 30-SECOND PERIODIC SHOUT FOR ADMIN (Continuous, never cleared prematurely)
  useEffect(() => {
    if (!autoShoutEnabled) return;

    const timer = setInterval(() => {
      if (soundAlertService.getIsMuted()) return;
      const now = Date.now();

      if (now - lastShoutTimeRef.current < 12000) return;

      const currentSnap = snapshotRef.current;
      const currentAdvisory = confirmedAdvisoryRef.current;
      const currentAlerts = alertsRef.current;

      const currentFatiguePct = currentAdvisory?.class_fatigue_pct ?? currentSnap?.class_fatigue_pct ?? 0;
      const currentCounts = currentSnap?.counts ?? { attentive: 28, distracted: 8, fatigued: 6 };
      const fatiguedCount = currentCounts.fatigued;
      const distractedCount = currentCounts.distracted;
      const unresolvedAlerts = currentAlerts.filter((a) => a.status !== 'Resolved');

      if (fatiguedCount > 0 || distractedCount > 0 || currentFatiguePct >= 20 || unresolvedAlerts.length > 0) {
        lastShoutTimeRef.current = now;
        const latestAlert = unresolvedAlerts[0];
        soundAlertService.shoutPeriodic30s({
          fatiguePct: currentFatiguePct,
          count: fatiguedCount,
          distractedCount: distractedCount,
          advisoryText: currentAdvisory?.message,
          activeAlertLabel: latestAlert ? `Student ${latestAlert.label}` : undefined,
        });
      }
    }, 30000); // 30-second interval

    return () => clearInterval(timer);
  }, [autoShoutEnabled]);

  const handleUpdateAlertStatus = async (alertId: number, nextStatus: AlertStatus) => {
    setUpdatingAlertId(alertId);
    try {
      const updated = await ApiService.updateAlertStatus(alertId, nextStatus);
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? updated : a)));
    } catch {
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === alertId ? { ...a, status: nextStatus } : a
        )
      );
    } finally {
      setUpdatingAlertId(null);
    }
  };

  const handleSelectSession = (sessionId: number) => {
    setSelectedSessionId(sessionId);
    mobileTelemetry.subscribeSession(sessionId);
    setSessionModalVisible(false);
    fetchAlerts(sessionId);
    // Reset trend data for newly switched session
    setAttPoints([]);
    setFatPoints([]);
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadSessions();
  };

  const currentSession = sessions.find((s) => s.id === selectedSessionId);
  const sessionDisplayName = currentSession
    ? `${currentSession.class_name || 'AI & DS - A Section'} (Room ${currentSession.room_name || 'A413'})`
    : 'AI & DS - A Section (Room A413)';

  const counts = snapshot?.counts ?? {
    attentive: 28,
    distracted: 8,
    fatigued: 6,
    unknown: 0,
  };

  const studentsDetected = snapshot?.students_detected || 42;
  const openAlerts = snapshot?.open_alerts ?? 2;
  const fatiguePct = confirmedAdvisory?.class_fatigue_pct ?? snapshot?.class_fatigue_pct ?? 62;

  const openFatigueCount = alerts.filter((a) => a.type === 'fatigue' && a.status !== 'Resolved').length;
  const openDistractionCount = alerts.filter((a) => a.type === 'distraction' && a.status !== 'Resolved').length;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.scrollContent}
      showsVerticalScrollIndicator={false}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#4F46E5']} />
      }
    >
      {/* Top Header Bar */}
      <View style={styles.topHeader}>
        <TouchableOpacity style={styles.iconBtn} activeOpacity={0.7} accessibilityLabel="Menu">
          <Menu size={22} color="#0F172A" />
        </TouchableOpacity>

        <View style={styles.userHeader}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>RS</Text>
          </View>
          <View style={styles.userTextContainer}>
            <Text style={styles.welcomeLabel}>Welcome</Text>
            <Text style={styles.userName}>Dr. Raman S</Text>
            <Text style={styles.userRole}>Admin</Text>
          </View>
        </View>

        <TouchableOpacity
          style={styles.iconBtn}
          activeOpacity={0.7}
          accessibilityLabel="Notifications"
          onPress={() => setIsAlertsModalVisible(true)}
        >
          <Bell size={22} color="#0F172A" />
        </TouchableOpacity>
      </View>

      {/* Offline banner if disconnected */}
      {!isWsConnected && !loading && (
        <OfflineState onRetry={() => mobileTelemetry.connect(selectedSessionId || undefined)} />
      )}

      {/* Select Session Dropdown */}
      <View style={styles.sessionSelectSection}>
        <Text style={styles.sessionSelectLabel}>Select Session</Text>
        <TouchableOpacity
          style={styles.dropdownSelector}
          activeOpacity={0.7}
          onPress={() => setSessionModalVisible(true)}
          accessibilityRole="combobox"
          accessibilityLabel={`Selected session: ${sessionDisplayName}`}
        >
          <Text style={styles.dropdownText} numberOfLines={1}>
            {sessionDisplayName}
          </Text>
          <ChevronDown size={18} color="#64748B" style={styles.dropdownChevron} />

          <View style={styles.liveBadge}>
            <Text style={styles.liveDot}>●</Text>
            <Text style={styles.liveText}>Live</Text>
          </View>
        </TouchableOpacity>
      </View>

      {/* Session Pick Modal */}
      <Modal
        visible={sessionModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setSessionModalVisible(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setSessionModalVisible(false)}
        >
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Choose Class Session</Text>
            {sessions.length === 0 ? (
              <Text style={styles.noSessionsText}>No active sessions found.</Text>
            ) : (
              sessions.map((s) => {
                const label = `${s.class_name || 'Class ' + s.classroom_id} (Room ${s.room_name || 'A' + s.classroom_id})`;
                const isSelected = s.id === selectedSessionId;
                return (
                  <TouchableOpacity
                    key={s.id}
                    style={[styles.sessionItem, isSelected && styles.sessionItemSelected]}
                    onPress={() => handleSelectSession(s.id)}
                  >
                    <Text style={[styles.sessionItemText, isSelected && styles.sessionItemTextSelected]}>
                      {label}
                    </Text>
                    {isSelected && <Check size={18} color="#4F46E5" />}
                  </TouchableOpacity>
                );
              })
            )}
          </View>
        </TouchableOpacity>
      </Modal>

      {/* 5 Stat Cards in horizontal row */}
      <View style={styles.statCardsRow}>
        <StatCard type="students" label="Students" value={studentsDetected} />
        <StatCard type="attentive" label="Attentive" value={counts.attentive} />
        <StatCard type="distracted" label="Distracted" value={counts.distracted} />
        <StatCard type="fatigued" label="Fatigued" value={counts.fatigued} />
        <StatCard type="alerts" label="Open Alerts" value={openAlerts} />
      </View>

      {/* Fatigue Advisory Banner */}
      <AdvisoryBanner
        advisory={confirmedAdvisory}
        fatiguePct={fatiguePct}
      />

      {/* Attention Trend Chart */}
      <TrendLineChart
        title="Attention Trend"
        subtitle="(Last 5 minutes)"
        color="blue"
        data={attPoints}
        isLive={isWsConnected}
      />

      {/* Fatigue Trend Chart */}
      <TrendLineChart
        title="Fatigue Trend"
        subtitle="(Last 5 minutes)"
        color="red"
        data={fatPoints}
        isLive={isWsConnected}
      />

      {/* Status Split (Current) Donut */}
      <StatusSplitDonut
        total={studentsDetected}
        attentive={counts.attentive}
        distracted={counts.distracted}
        fatigued={counts.fatigued}
      />

      {/* Recent Alert Count Card */}
      <RecentAlertCard
        openAlerts={openAlerts}
        fatigueCount={openFatigueCount}
        distractionCount={openDistractionCount}
        onPress={() => setIsAlertsModalVisible(true)}
      />

      {/* Student Behavior Alerts Modal */}
      {isAlertsModalVisible && (
        <StudentBehaviorAlertsModal
          visible={isAlertsModalVisible}
          onClose={() => setIsAlertsModalVisible(false)}
          alerts={alerts}
          onUpdateStatus={handleUpdateAlertStatus}
          onRefresh={() => fetchAlerts(selectedSessionId || undefined)}
          className={sessionDisplayName}
          isUpdatingId={updatingAlertId}
        />
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8FAFC',
  },
  scrollContent: {
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 24,
  },
  topHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 8,
    marginBottom: 8,
  },
  iconBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
  },
  userHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#C7D2FE',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
    borderWidth: 2,
    borderColor: '#FFFFFF',
  },
  avatarText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#3730A3',
  },
  userTextContainer: {
    justifyContent: 'center',
  },
  welcomeLabel: {
    fontSize: 10.5,
    color: '#64748B',
    fontWeight: '500',
  },
  userName: {
    fontSize: 13.5,
    fontWeight: '700',
    color: '#0F172A',
    lineHeight: 16,
  },
  userRole: {
    fontSize: 10.5,
    color: '#64748B',
  },
  sessionSelectSection: {
    marginBottom: 14,
  },
  sessionSelectLabel: {
    fontSize: 11,
    color: '#64748B',
    fontWeight: '500',
    marginBottom: 4,
  },
  dropdownSelector: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.03,
    shadowRadius: 2,
  },
  dropdownText: {
    flex: 1,
    fontSize: 13.5,
    fontWeight: '600',
    color: '#0F172A',
  },
  dropdownChevron: {
    marginHorizontal: 8,
  },
  liveBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#DCFCE7',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
  },
  liveDot: {
    color: '#15803D',
    fontSize: 8.5,
    marginRight: 3,
  },
  liveText: {
    color: '#15803D',
    fontSize: 10.5,
    fontWeight: '700',
  },
  statCardsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  modalContent: {
    width: '100%',
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 20,
    maxHeight: 350,
  },
  modalTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 14,
  },
  noSessionsText: {
    fontSize: 13,
    color: '#64748B',
    paddingVertical: 12,
  },
  sessionItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 10,
    borderRadius: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  sessionItemSelected: {
    backgroundColor: '#EEF2FF',
  },
  sessionItemText: {
    fontSize: 13.5,
    color: '#334155',
  },
  sessionItemTextSelected: {
    fontWeight: '700',
    color: '#4F46E5',
  },
});
