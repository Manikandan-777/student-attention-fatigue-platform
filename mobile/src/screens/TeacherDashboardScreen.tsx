import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
  Image,
} from 'react-native';
import { Menu, Bell, Volume2, VolumeX, Megaphone } from 'lucide-react-native';
import { THEME } from '../theme';
import { ApiService } from '../services/api';
import { mobileTelemetry } from '../services/websocket';
import { speechService, soundAlertService } from '../services/soundAlert';
import { StatCard } from '../components/StatCard';
import { AdvisoryBanner, getFatigueMessage } from '../components/AdvisoryBanner';
import { TrendLineChart } from '../components/TrendLineChart';
import { StatusSplitDonut } from '../components/StatusSplitDonut';
import { RecentAlertCard } from '../components/RecentAlertCard';
import { StudentBehaviorAlertCard } from '../components/StudentBehaviorAlertCard';
import { StudentBehaviorAlertsModal } from '../components/StudentBehaviorAlertsModal';
import { EmptySessionState } from '../components/EmptySessionState';
import { OfflineState } from '../components/OfflineState';
import { Alert, AlertStatus, ClassSnapshot, FatigueAdvisory } from '../types';

interface TeacherDashboardScreenProps {
  onNavigateTab?: (tab: string) => void;
}

const INITIAL_DEMO_ALERTS: Alert[] = [
  {
    id: 101,
    session_id: 12,
    track_id: 1,
    label: 'S001',
    type: 'fatigue',
    status: 'New',
    message: 'Frequent yawning and eyelid closure observed over last 60s',
    confidence: 0.94,
    created_at: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
  },
  {
    id: 102,
    session_id: 12,
    track_id: 4,
    label: 'S004',
    type: 'distraction',
    status: 'New',
    message: 'Sustained head yaw away from teacher / off-task gaze detected for > 15s',
    confidence: 0.88,
    created_at: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
  },
];

export const TeacherDashboardScreen: React.FC<TeacherDashboardScreenProps> = ({
  onNavigateTab,
}) => {
  const [snapshot, setSnapshot] = useState<ClassSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [isWsConnected, setIsWsConnected] = useState(false);

  // Student Behavior Alerts & Voice Speech states
  const [alerts, setAlerts] = useState<Alert[]>(INITIAL_DEMO_ALERTS);
  const [alertsFilter, setAlertsFilter] = useState<'all' | 'fatigue' | 'distraction'>('all');
  const [isAlertsModalVisible, setIsAlertsModalVisible] = useState(false);
  const [updatingAlertId, setUpdatingAlertId] = useState<number | null>(null);
  const [isVoiceMuted, setIsVoiceMuted] = useState(speechService.getIsMuted());

  // Live trend points (Attention & Fatigue)
  const [attPoints, setAttPoints] = useState<Array<{ ts: string; value: number }>>([]);
  const [fatPoints, setFatPoints] = useState<Array<{ ts: string; value: number }>>([]);

  // Hysteresis for fatigue advisory (STATUS_HYSTERESIS_S = 3s)
  const [confirmedAdvisory, setConfirmedAdvisory] = useState<FatigueAdvisory | null>(null);
  const candidateLevelRef = useRef<{ level: number; since: number; advisory: FatigueAdvisory } | null>(null);

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
    const fatiguedCount = snap.counts?.fatigued ?? 0;
    const isHigh = fatPct >= 35 || fatiguedCount >= 3 || (adv?.level ?? 0) >= 2;
    const now = Date.now();

    if (isHigh && (now - lastHighFatigueShoutRef.current >= 18000)) {
      lastHighFatigueShoutRef.current = now;
      lastShoutTimeRef.current = now;
      soundAlertService.shoutImmediateHighFatigue({
        fatiguePct: fatPct,
        count: fatiguedCount,
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
      // Keep demo/existing alerts if offline
    }
  };

  const initialTimeoutRef = useRef<any>(null);

  const fetchDashboard = async () => {
    try {
      const data = await ApiService.getTeacherDashboard();
      if (data) {
        setSnapshot(data);
        snapshotRef.current = data;
        if (data.fatigue_advisory) {
          setConfirmedAdvisory(data.fatigue_advisory);
          confirmedAdvisoryRef.current = data.fatigue_advisory;
        }
        fetchAlerts(data.session_id);

        // IMMEDIATE SHOUT: If class is already in high fatigue when dashboard loads, shout immediately!
        if (initialTimeoutRef.current) clearTimeout(initialTimeoutRef.current);
        initialTimeoutRef.current = setTimeout(() => {
          checkAndShoutHighFatigue(data, data.fatigue_advisory);
        }, 800);
      }
    } catch {
      // Keep last available data
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    let isMounted = true;

    fetchDashboard();

    // Connect to WebSocket telemetry stream (§5: same source, same numbers as website)
    mobileTelemetry.connect();

    const unsubTel = mobileTelemetry.onTelemetry(({ snapshot: liveSnap, ts }) => {
      if (!isMounted || !liveSnap) return;

      setSnapshot(liveSnap);
      snapshotRef.current = liveSnap;

      const timeLabel = ts ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      // Update Attention trend points
      if (liveSnap.avg_attention_score !== undefined) {
        setAttPoints((prev) => {
          const next = [...prev, { ts: timeLabel, value: liveSnap.avg_attention_score }];
          return next.slice(-20); // Keep last 20 points
        });
      }

      // Compute or retrieve class fatigue pct
      const fatPct = liveSnap.fatigue_advisory?.class_fatigue_pct ?? liveSnap.class_fatigue_pct ?? 0;
      setFatPoints((prev) => {
        const next = [...prev, { ts: timeLabel, value: fatPct }];
        return next.slice(-20);
      });

      // IMMEDIATE SHOUT: Trigger whenever live high fatigue is detected
      checkAndShoutHighFatigue(liveSnap, liveSnap.fatigue_advisory);

      // Apply 3-second hold hysteresis on advisory message (avoid flicker)
      const rawLevel = liveSnap.fatigue_advisory?.level ?? getFatigueMessage(fatPct).level;

      if (confirmedAdvisoryRef.current && confirmedAdvisoryRef.current.level !== rawLevel) {
        if (candidateLevelRef.current?.level === rawLevel) {
          if (Date.now() - candidateLevelRef.current.since >= 3000) {
            const nextAdv = liveSnap.fatigue_advisory ?? {
              level: rawLevel,
              class_fatigue_pct: fatPct,
              code: 'CONTINUE',
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
              code: 'CONTINUE',
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

    // Real-time alert listener for student behaviors with voice speech
    const unsubAlert = mobileTelemetry.onAlert((newAlert) => {
      if (!isMounted || !newAlert) return;

      setAlerts((prev) => {
        const exists = prev.some((a) => a.id === newAlert.id);
        const updated = exists ? prev.map((a) => (a.id === newAlert.id ? newAlert : a)) : [newAlert, ...prev];
        alertsRef.current = updated;
        return updated;
      });

      // Announce newly triggered student behavior alert
      if (newAlert.status === 'New' && autoShoutEnabledRef.current && !soundAlertService.getIsMuted()) {
        const curFatPct = confirmedAdvisoryRef.current?.class_fatigue_pct ?? snapshotRef.current?.class_fatigue_pct ?? 0;
        if (newAlert.type === 'fatigue' && (newAlert.confidence >= 0.85 || curFatPct >= 35)) {
          // IMMEDIATE SHOUT for high fatigue behavior
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
      if (initialTimeoutRef.current) clearTimeout(initialTimeoutRef.current);
      unsubTel();
      unsubConn();
      unsubAlert();
    };
  }, []);

  // AUTOMATIC 30-SECOND SHOUT LOOP (Continuous, never cleared by telemetry state changes)
  useEffect(() => {
    if (!autoShoutEnabled) return;

    const intervalTimer = setInterval(() => {
      if (soundAlertService.getIsMuted()) return;
      const now = Date.now();

      // Don't collide if an emergency shout happened recently (< 12s)
      if (now - lastShoutTimeRef.current < 12000) return;

      const currentSnap = snapshotRef.current;
      const currentAdvisory = confirmedAdvisoryRef.current;
      const currentAlerts = alertsRef.current;

      const currentFatiguePct = currentAdvisory?.class_fatigue_pct ?? currentSnap?.class_fatigue_pct ?? 0;
      const currentCounts = currentSnap?.counts ?? { attentive: 28, distracted: 8, fatigued: 6 };
      const fatiguedCount = currentCounts.fatigued;
      const distractedCount = currentCounts.distracted;
      const unresolvedAlerts = currentAlerts.filter((a) => a.status !== 'Resolved');

      // Auto-shout if there are fatigued or distracted students or active alerts or fatigue pct
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
    }, 30000); // Exactly every 30 seconds

    return () => clearInterval(intervalTimer);
  }, [autoShoutEnabled]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchDashboard();
  };

  const handleToggleVoice = () => {
    const nextMuted = soundAlertService.toggleMute();
    setIsVoiceMuted(nextMuted);
    if (!nextMuted) {
      soundAlertService.playAlertSound();
      soundAlertService.speakText('Sound and voice alerts enabled');
    }
  };

  const handleTestVoiceAlert = () => {
    soundAlertService.testAlert();
  };

  const handleTestHighFatigueShout = () => {
    soundAlertService.testHighFatigueAlert();
  };

  const handleTestPeriodic30sShout = () => {
    soundAlertService.testPeriodic30sAlert();
  };

  const handleUpdateAlertStatus = async (alertId: number, nextStatus: AlertStatus) => {
    setUpdatingAlertId(alertId);
    try {
      const updated = await ApiService.updateAlertStatus(alertId, nextStatus);
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? updated : a)));
    } catch {
      // Optimistic update if offline
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === alertId
            ? {
                ...a,
                status: nextStatus,
                viewed_at: nextStatus === 'Viewed' ? new Date().toISOString() : a.viewed_at,
                resolved_at: nextStatus === 'Resolved' ? new Date().toISOString() : a.resolved_at,
              }
            : a
        )
      );
    } finally {
      setUpdatingAlertId(null);
    }
  };

  const counts = snapshot?.counts ?? {
    attentive: 28,
    distracted: 8,
    fatigued: 6,
    unknown: 0,
  };

  const studentsDetected = snapshot?.students_detected || 42;
  const openAlerts = snapshot?.open_alerts ?? 2;
  const className = snapshot?.class_name || 'AI & DS - A Section';
  const fatiguePct = confirmedAdvisory?.class_fatigue_pct ?? snapshot?.class_fatigue_pct ?? 38;

  const openFatigueCount = alerts.filter((a) => a.type === 'fatigue' && a.status !== 'Resolved').length;
  const openDistractionCount = alerts.filter((a) => a.type === 'distraction' && a.status !== 'Resolved').length;
  const openBehaviorAlerts = alerts.filter((a) => a.status !== 'Resolved').length;

  const displayedAlerts = alerts.filter((a) => {
    if (alertsFilter === 'fatigue') return a.type === 'fatigue';
    if (alertsFilter === 'distraction') return a.type === 'distraction';
    return true;
  });

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
          {/* Avatar circle */}
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>AK</Text>
          </View>
          <View style={styles.userTextContainer}>
            <Text style={styles.welcomeLabel}>Welcome</Text>
            <Text style={styles.userName}>Mr. Aravind K</Text>
            <Text style={styles.userRole}>Teacher</Text>
          </View>
        </View>

        <View style={styles.headerRightActions}>
          {/* Voice Speech Toggle */}
          <TouchableOpacity
            style={[styles.iconBtn, isVoiceMuted && styles.voiceBtnMuted]}
            activeOpacity={0.7}
            onPress={handleToggleVoice}
            accessibilityLabel={isVoiceMuted ? 'Unmute voice alerts' : 'Mute voice alerts'}
          >
            {isVoiceMuted ? (
              <VolumeX size={20} color="#EF4444" />
            ) : (
              <Volume2 size={20} color="#4F46E5" />
            )}
          </TouchableOpacity>

          {/* Bell Notifications */}
          <TouchableOpacity
            style={styles.iconBtn}
            activeOpacity={0.7}
            accessibilityLabel="Notifications"
            onPress={() => setIsAlertsModalVisible(true)}
          >
            <Bell size={22} color="#0F172A" />
            {openBehaviorAlerts > 0 && (
              <View style={styles.bellBadge}>
                <Text style={styles.bellBadgeText}>{openBehaviorAlerts}</Text>
              </View>
            )}
          </TouchableOpacity>
        </View>
      </View>

      {/* Offline banner if disconnected */}
      {!isWsConnected && !loading && (
        <OfflineState onRetry={() => mobileTelemetry.connect()} />
      )}

      {/* No Class Running state */}
      {!snapshot && !loading && isWsConnected ? (
        <EmptySessionState />
      ) : (
        <>
          {/* Current Class Header */}
          <View style={styles.classHeader}>
            <View>
              <Text style={styles.classSublabel}>Current Class</Text>
              <Text style={styles.className}>{className}</Text>
            </View>
            <View style={styles.liveBadge}>
              <Text style={styles.liveDot}>●</Text>
              <Text style={styles.liveText}>Live {studentsDetected}</Text>
            </View>
          </View>

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

            {/* Student Behavior Alerts Section */}
          <View style={styles.behaviorSection}>
            <View style={styles.behaviorHeaderRow}>
              <View style={styles.behaviorTitleGroup}>
                <Text style={styles.behaviorTitle}>Student Behavior Alerts</Text>
                <Text style={styles.behaviorSubtitle}>
                  Real-time alerts for student fatigue & attention with automatic voice shout
                </Text>
              </View>
              <TouchableOpacity
                style={styles.viewAllBtn}
                onPress={() => setIsAlertsModalVisible(true)}
                activeOpacity={0.7}
                accessibilityLabel={`View all ${alerts.length} behavior alerts`}
              >
                <Text style={styles.viewAllBtnText}>View All ({alerts.length})</Text>
              </TouchableOpacity>
            </View>

            {/* Auto-Shout Status & Interval Control Banner */}
            <View style={styles.autoShoutBanner}>
              <View style={styles.autoShoutLeft}>
                <View style={[styles.pulseDot, autoShoutEnabled && !isVoiceMuted ? styles.pulseDotActive : styles.pulseDotInactive]} />
                <View style={styles.autoShoutTextGroup}>
                  <Text style={styles.autoShoutTitle}>Auto-Shout: 30s Loop & High Fatigue Immediate</Text>
                  <Text style={styles.autoShoutSubtitle}>
                    {isVoiceMuted
                      ? 'Audio muted (unmute at top right)'
                      : autoShoutEnabled
                      ? 'Active • High fatigue triggers immediate emergency siren • 30s status loop'
                      : 'Auto-shout paused'}
                  </Text>
                </View>
              </View>
              <TouchableOpacity
                testID="auto-shout-toggle-btn"
                style={[styles.autoShoutToggleBtn, autoShoutEnabled && styles.autoShoutToggleBtnActive]}
                onPress={() => setAutoShoutEnabled(!autoShoutEnabled)}
                activeOpacity={0.7}
              >
                <Text style={[styles.autoShoutToggleText, autoShoutEnabled && styles.autoShoutToggleTextActive]}>
                  {autoShoutEnabled ? 'ON' : 'OFF'}
                </Text>
              </TouchableOpacity>
            </View>

            {/* Quick Shout Action & Test Buttons */}
            <View style={styles.shoutActionsRow}>
              <TouchableOpacity
                testID="test-voice-btn"
                style={styles.voiceTestBtn}
                onPress={handleTestVoiceAlert}
                activeOpacity={0.7}
                accessibilityLabel="Test Voice Alert"
              >
                <Megaphone size={12} color="#4F46E5" />
                <Text style={styles.voiceTestBtnText}>Test Voice</Text>
              </TouchableOpacity>

              <TouchableOpacity
                testID="test-high-fatigue-btn"
                style={[styles.voiceTestBtn, styles.highFatigueTestBtn]}
                onPress={handleTestHighFatigueShout}
                activeOpacity={0.7}
                accessibilityLabel="Immediate High Fatigue Shout"
              >
                <Text style={styles.highFatigueTestBtnText}>⚡ High Fatigue Shout</Text>
              </TouchableOpacity>

              <TouchableOpacity
                testID="test-periodic-30s-btn"
                style={[styles.voiceTestBtn, styles.periodicTestBtn]}
                onPress={handleTestPeriodic30sShout}
                activeOpacity={0.7}
                accessibilityLabel="Test 30s Periodic Shout"
              >
                <Text style={styles.periodicTestBtnText}>⏱ 30s Shout</Text>
              </TouchableOpacity>
            </View>

            {/* Behavior Filter Chips */}
            <View style={styles.filterRow}>
              <TouchableOpacity
                testID="filter-chip-all"
                style={[styles.filterChip, alertsFilter === 'all' && styles.filterChipActive]}
                onPress={() => setAlertsFilter('all')}
              >
                <Text
                  style={[
                    styles.filterChipText,
                    alertsFilter === 'all' && styles.filterChipTextActive,
                  ]}
                >
                  All ({alerts.length})
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                testID="filter-chip-fatigue"
                style={[
                  styles.filterChip,
                  alertsFilter === 'fatigue' && styles.filterChipActiveFatigue,
                ]}
                onPress={() => setAlertsFilter('fatigue')}
              >
                <Text
                  style={[
                    styles.filterChipText,
                    alertsFilter === 'fatigue' && styles.filterChipTextActiveFatigue,
                  ]}
                >
                  Fatigue ({openFatigueCount})
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                testID="filter-chip-distraction"
                style={[
                  styles.filterChip,
                  alertsFilter === 'distraction' && styles.filterChipActiveDistraction,
                ]}
                onPress={() => setAlertsFilter('distraction')}
              >
                <Text
                  style={[
                    styles.filterChipText,
                    alertsFilter === 'distraction' && styles.filterChipTextActiveDistraction,
                  ]}
                >
                  Inattentive ({openDistractionCount})
                </Text>
              </TouchableOpacity>
            </View>

            {/* Inline Behavior Alert Cards */}
            {displayedAlerts.length === 0 ? (
              <View style={styles.emptyBehaviorCard}>
                <Text style={styles.emptyBehaviorText}>
                  ✓ No alerts for this filter. All students are attentive!
                </Text>
              </View>
            ) : (
              displayedAlerts.slice(0, 3).map((item) => (
                <StudentBehaviorAlertCard
                  key={item.id}
                  alert={item}
                  onUpdateStatus={handleUpdateAlertStatus}
                  isUpdating={updatingAlertId === item.id}
                />
              ))
            )}
          </View>
        </>
      )}

      {/* Interactive Student Behavior Alerts Modal */}
      {isAlertsModalVisible && (
        <StudentBehaviorAlertsModal
          visible={isAlertsModalVisible}
          onClose={() => setIsAlertsModalVisible(false)}
          alerts={alerts}
          onUpdateStatus={handleUpdateAlertStatus}
          onRefresh={() => fetchAlerts(snapshot?.session_id)}
          className={className}
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
    marginBottom: 12,
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
  classHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 14,
  },
  classSublabel: {
    fontSize: 11,
    color: '#64748B',
    fontWeight: '500',
  },
  className: {
    fontSize: 15,
    fontWeight: '700',
    color: '#0F172A',
    marginTop: 2,
  },
  liveBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#DCFCE7',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 14,
  },
  liveDot: {
    color: '#15803D',
    fontSize: 9,
    marginRight: 4,
  },
  liveText: {
    color: '#15803D',
    fontSize: 11,
    fontWeight: '700',
  },
  statCardsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  headerRightActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  voiceBtnMuted: {
    backgroundColor: '#FEE2E2',
  },
  bellBadge: {
    position: 'absolute',
    top: 2,
    right: 2,
    backgroundColor: '#DC2626',
    borderRadius: 8,
    minWidth: 16,
    height: 16,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 3,
  },
  bellBadgeText: {
    color: '#FFFFFF',
    fontSize: 9,
    fontWeight: '800',
  },
  behaviorSection: {
    marginTop: 14,
    marginBottom: 20,
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
    borderColor: '#F1F5F9',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 3,
  },
  behaviorHeaderRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  behaviorTitleGroup: {
    flex: 1,
    paddingRight: 6,
  },
  behaviorTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0F172A',
  },
  behaviorSubtitle: {
    fontSize: 11,
    color: '#64748B',
    marginTop: 2,
  },
  autoShoutBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#F8FAFC',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 9,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  autoShoutLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    paddingRight: 8,
  },
  pulseDot: {
    width: 9,
    height: 9,
    borderRadius: 4.5,
    marginRight: 8,
  },
  pulseDotActive: {
    backgroundColor: '#10B981',
  },
  pulseDotInactive: {
    backgroundColor: '#94A3B8',
  },
  autoShoutTextGroup: {
    flex: 1,
  },
  autoShoutTitle: {
    fontSize: 11.5,
    fontWeight: '700',
    color: '#0F172A',
  },
  autoShoutSubtitle: {
    fontSize: 9.5,
    color: '#64748B',
    marginTop: 1,
  },
  autoShoutToggleBtn: {
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderRadius: 8,
    backgroundColor: '#E2E8F0',
  },
  autoShoutToggleBtnActive: {
    backgroundColor: '#DCFCE7',
  },
  autoShoutToggleText: {
    fontSize: 10.5,
    fontWeight: '700',
    color: '#64748B',
  },
  autoShoutToggleTextActive: {
    color: '#15803D',
  },
  shoutActionsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 10,
    flexWrap: 'wrap',
  },
  behaviorActionBtns: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  voiceTestBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: 8,
    backgroundColor: '#EEF2FF',
    borderWidth: 1,
    borderColor: '#C7D2FE',
  },
  voiceTestBtnText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#4F46E5',
  },
  highFatigueTestBtn: {
    backgroundColor: '#FEE2E2',
    borderColor: '#FECACA',
  },
  highFatigueTestBtnText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#DC2626',
  },
  periodicTestBtn: {
    backgroundColor: '#FEF3C7',
    borderColor: '#FDE68A',
  },
  periodicTestBtnText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#B45309',
  },
  viewAllBtn: {
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: 8,
    backgroundColor: '#F1F5F9',
  },
  viewAllBtnText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#475569',
  },
  filterRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 10,
  },
  filterChip: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    backgroundColor: '#F8FAFC',
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  filterChipActive: {
    backgroundColor: '#EEF2FF',
    borderColor: '#C7D2FE',
  },
  filterChipActiveFatigue: {
    backgroundColor: '#FEE2E2',
    borderColor: '#FECACA',
  },
  filterChipActiveDistraction: {
    backgroundColor: '#FEF3C7',
    borderColor: '#FDE68A',
  },
  filterChipText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#64748B',
  },
  filterChipTextActive: {
    color: '#4F46E5',
    fontWeight: '700',
  },
  filterChipTextActiveFatigue: {
    color: '#DC2626',
    fontWeight: '700',
  },
  filterChipTextActiveDistraction: {
    color: '#D97706',
    fontWeight: '700',
  },
  emptyBehaviorCard: {
    paddingVertical: 20,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F8FAFC',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  emptyBehaviorText: {
    fontSize: 12,
    color: '#64748B',
    fontWeight: '500',
  },
});
