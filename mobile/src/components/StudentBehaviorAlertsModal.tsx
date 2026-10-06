import React, { useState } from 'react';
import {
  Modal,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { X, Bell, RefreshCw, AlertOctagon, EyeOff, CheckCircle2 } from 'lucide-react-native';
import { Alert, AlertStatus } from '../types';
import { StudentBehaviorAlertCard } from './StudentBehaviorAlertCard';

interface StudentBehaviorAlertsModalProps {
  visible: boolean;
  onClose: () => void;
  alerts: Alert[];
  onUpdateStatus: (alertId: number, nextStatus: AlertStatus) => Promise<void>;
  onRefresh?: () => void;
  className?: string;
  isUpdatingId?: number | null;
}

type FilterTab = 'all' | 'fatigue' | 'distraction' | 'resolved';

export const StudentBehaviorAlertsModal: React.FC<StudentBehaviorAlertsModalProps> = ({
  visible,
  onClose,
  alerts,
  onUpdateStatus,
  onRefresh,
  className = 'Current Class',
  isUpdatingId,
}) => {
  const [activeTab, setActiveTab] = useState<FilterTab>('all');

  const fatigueCount = alerts.filter((a) => a.type === 'fatigue' && a.status !== 'Resolved').length;
  const distractionCount = alerts.filter(
    (a) => a.type === 'distraction' && a.status !== 'Resolved'
  ).length;
  const resolvedCount = alerts.filter((a) => a.status === 'Resolved').length;
  const activeCount = alerts.filter((a) => a.status !== 'Resolved').length;

  const filteredAlerts = alerts.filter((a) => {
    if (activeTab === 'fatigue') return a.type === 'fatigue' && a.status !== 'Resolved';
    if (activeTab === 'distraction') return a.type === 'distraction' && a.status !== 'Resolved';
    if (activeTab === 'resolved') return a.status === 'Resolved';
    return true; // 'all'
  });

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={false}
      onRequestClose={onClose}
    >
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.container}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerTitleContainer}>
              <View style={styles.iconCircle}>
                <Bell size={20} color="#EA580C" />
              </View>
              <View>
                <Text style={styles.title}>Student Behavior Alerts</Text>
                <Text style={styles.subtitle}>{className}</Text>
              </View>
            </View>

            <View style={styles.headerActions}>
              {onRefresh && (
                <TouchableOpacity
                  onPress={onRefresh}
                  style={styles.iconBtn}
                  accessibilityLabel="Refresh alerts"
                >
                  <RefreshCw size={18} color="#475569" />
                </TouchableOpacity>
              )}
              <TouchableOpacity
                onPress={onClose}
                style={styles.closeBtn}
                accessibilityLabel="Close alerts view"
              >
                <X size={20} color="#0F172A" />
              </TouchableOpacity>
            </View>
          </View>

          {/* Filter Tabs */}
          <View style={styles.tabsRow}>
            <TouchableOpacity
              style={[styles.tab, activeTab === 'all' && styles.tabActive]}
              onPress={() => setActiveTab('all')}
              accessibilityRole="tab"
              accessibilityLabel={`All alerts, ${alerts.length}`}
            >
              <Text style={[styles.tabText, activeTab === 'all' && styles.tabTextActive]}>
                All
              </Text>
              <View
                style={[
                  styles.tabBadge,
                  activeTab === 'all' ? styles.tabBadgeActive : styles.tabBadgeInactive,
                ]}
              >
                <Text
                  style={[
                    styles.tabBadgeText,
                    activeTab === 'all' && styles.tabBadgeTextActive,
                  ]}
                >
                  {alerts.length}
                </Text>
              </View>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.tab, activeTab === 'fatigue' && styles.tabActive]}
              onPress={() => setActiveTab('fatigue')}
              accessibilityRole="tab"
              accessibilityLabel={`Fatigue alerts, ${fatigueCount}`}
            >
              <AlertOctagon size={14} color={activeTab === 'fatigue' ? '#DC2626' : '#64748B'} />
              <Text
                style={[
                  styles.tabText,
                  activeTab === 'fatigue' && { color: '#DC2626', fontWeight: '700' },
                ]}
              >
                Fatigue
              </Text>
              <View
                style={[
                  styles.tabBadge,
                  { backgroundColor: activeTab === 'fatigue' ? '#FEE2E2' : '#F1F5F9' },
                ]}
              >
                <Text
                  style={[
                    styles.tabBadgeText,
                    { color: activeTab === 'fatigue' ? '#DC2626' : '#64748B' },
                  ]}
                >
                  {fatigueCount}
                </Text>
              </View>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.tab, activeTab === 'distraction' && styles.tabActive]}
              onPress={() => setActiveTab('distraction')}
              accessibilityRole="tab"
              accessibilityLabel={`Inattentive alerts, ${distractionCount}`}
            >
              <EyeOff size={14} color={activeTab === 'distraction' ? '#D97706' : '#64748B'} />
              <Text
                style={[
                  styles.tabText,
                  activeTab === 'distraction' && { color: '#D97706', fontWeight: '700' },
                ]}
              >
                Inattentive
              </Text>
              <View
                style={[
                  styles.tabBadge,
                  { backgroundColor: activeTab === 'distraction' ? '#FEF3C7' : '#F1F5F9' },
                ]}
              >
                <Text
                  style={[
                    styles.tabBadgeText,
                    { color: activeTab === 'distraction' ? '#D97706' : '#64748B' },
                  ]}
                >
                  {distractionCount}
                </Text>
              </View>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.tab, activeTab === 'resolved' && styles.tabActive]}
              onPress={() => setActiveTab('resolved')}
              accessibilityRole="tab"
              accessibilityLabel={`Resolved alerts, ${resolvedCount}`}
            >
              <CheckCircle2 size={14} color={activeTab === 'resolved' ? '#16A34A' : '#64748B'} />
              <Text
                style={[
                  styles.tabText,
                  activeTab === 'resolved' && { color: '#16A34A', fontWeight: '700' },
                ]}
              >
                Resolved
              </Text>
              <View
                style={[
                  styles.tabBadge,
                  { backgroundColor: activeTab === 'resolved' ? '#DCFCE7' : '#F1F5F9' },
                ]}
              >
                <Text
                  style={[
                    styles.tabBadgeText,
                    { color: activeTab === 'resolved' ? '#16A34A' : '#64748B' },
                  ]}
                >
                  {resolvedCount}
                </Text>
              </View>
            </TouchableOpacity>
          </View>

          {/* Alert List */}
          <ScrollView
            style={styles.list}
            contentContainerStyle={styles.listContent}
            showsVerticalScrollIndicator={false}
          >
            {filteredAlerts.length === 0 ? (
              <View style={styles.emptyContainer}>
                <View style={styles.emptyIconCircle}>
                  <CheckCircle2 size={32} color="#16A34A" />
                </View>
                <Text style={styles.emptyTitle}>No behavior alerts</Text>
                <Text style={styles.emptySubtitle}>
                  {activeTab === 'fatigue'
                    ? 'No students currently showing fatigue indicators.'
                    : activeTab === 'distraction'
                    ? 'No students currently marked inattentive or distracted.'
                    : activeTab === 'resolved'
                    ? 'No resolved alerts in this session.'
                    : 'All students are attentive and no behavioral alerts are open!'}
                </Text>
              </View>
            ) : (
              filteredAlerts.map((item) => (
                <StudentBehaviorAlertCard
                  key={item.id}
                  alert={item}
                  onUpdateStatus={onUpdateStatus}
                  isUpdating={isUpdatingId === item.id}
                />
              ))
            )}
          </ScrollView>
        </View>
      </SafeAreaView>
    </Modal>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#F8FAFC',
  },
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 14,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  headerTitleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  iconCircle: {
    width: 38,
    height: 38,
    borderRadius: 12,
    backgroundColor: '#FFF7ED',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0F172A',
  },
  subtitle: {
    fontSize: 12,
    color: '#64748B',
    marginTop: 2,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  iconBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#F1F5F9',
    alignItems: 'center',
    justifyContent: 'center',
  },
  closeBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#F1F5F9',
    alignItems: 'center',
    justifyContent: 'center',
  },
  tabsRow: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
    gap: 8,
  },
  tab: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: '#F8FAFC',
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  tabActive: {
    backgroundColor: '#EFF6FF',
    borderColor: '#BFDBFE',
  },
  tabText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#475569',
  },
  tabTextActive: {
    color: '#1D4ED8',
    fontWeight: '700',
  },
  tabBadge: {
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 8,
  },
  tabBadgeActive: {
    backgroundColor: '#DBEAFE',
  },
  tabBadgeInactive: {
    backgroundColor: '#E2E8F0',
  },
  tabBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#475569',
  },
  tabBadgeTextActive: {
    color: '#1D4ED8',
  },
  list: {
    flex: 1,
  },
  listContent: {
    padding: 16,
    paddingBottom: 32,
  },
  emptyContainer: {
    paddingVertical: 60,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  emptyIconCircle: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#DCFCE7',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 6,
  },
  emptySubtitle: {
    fontSize: 13,
    color: '#64748B',
    textAlign: 'center',
    lineHeight: 18,
  },
});
