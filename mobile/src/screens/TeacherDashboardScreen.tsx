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
import { Menu, Bell } from 'lucide-react-native';
import { THEME } from '../theme';
import { ApiService } from '../services/api';
import { mobileTelemetry } from '../services/websocket';
import { StatCard } from '../components/StatCard';
import { AdvisoryBanner, getFatigueMessage } from '../components/AdvisoryBanner';
import { TrendLineChart } from '../components/TrendLineChart';
import { StatusSplitDonut } from '../components/StatusSplitDonut';
import { RecentAlertCard } from '../components/RecentAlertCard';
import { EmptySessionState } from '../components/EmptySessionState';
import { OfflineState } from '../components/OfflineState';
import { ClassSnapshot, FatigueAdvisory } from '../types';

interface TeacherDashboardScreenProps {
  onNavigateTab?: (tab: string) => void;
}

export const TeacherDashboardScreen: React.FC<TeacherDashboardScreenProps> = ({
  onNavigateTab,
}) => {
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

  const fetchDashboard = async () => {
    try {
      const data = await ApiService.getTeacherDashboard();
      if (data) {
        setSnapshot(data);
        if (data.fatigue_advisory) {
          setConfirmedAdvisory(data.fatigue_advisory);
        }
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

      // Apply 3-second hold hysteresis on advisory message (avoid flicker)
      const rawLevel = liveSnap.fatigue_advisory?.level ?? getFatigueMessage(fatPct).level;
      const now = Date.now();

      if (confirmedAdvisory && confirmedAdvisory.level !== rawLevel) {
        if (candidateLevelRef.current?.level === rawLevel) {
          if (now - candidateLevelRef.current.since >= 3000) {
            setConfirmedAdvisory(liveSnap.fatigue_advisory ?? {
              level: rawLevel,
              class_fatigue_pct: fatPct,
              code: 'CONTINUE',
              message: getFatigueMessage(fatPct).text,
              usable_tracks: liveSnap.students_detected,
              since: new Date().toISOString(),
            });
            candidateLevelRef.current = null;
          }
        } else {
          candidateLevelRef.current = {
            level: rawLevel,
            since: now,
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
        }
      }
    });

    const unsubConn = mobileTelemetry.onConnectionChange((connected) => {
      if (isMounted) setIsWsConnected(connected);
    });

    return () => {
      isMounted = false;
      unsubTel();
      unsubConn();
    };
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    fetchDashboard();
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

        <TouchableOpacity style={styles.iconBtn} activeOpacity={0.7} accessibilityLabel="Notifications">
          <Bell size={22} color="#0F172A" />
        </TouchableOpacity>
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
            isOffline={!isWsConnected}
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
            onPress={() => onNavigateTab?.('Dashboard')}
          />
        </>
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
});
