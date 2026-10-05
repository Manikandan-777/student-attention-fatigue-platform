import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { LogOut, ChevronRight } from 'lucide-react-native';
import { THEME } from '../theme';
import { StorageService } from '../services/storage';
import { StatusBadge } from '../components/StatusBadge';

interface TeacherProfileScreenProps {
  role?: 'teacher' | 'admin';
  username?: string;
  displayName?: string;
  classroomName?: string;
  onLogout: () => void;
}

export const TeacherProfileScreen: React.FC<TeacherProfileScreenProps> = ({
  role = 'teacher',
  username: initialUsername,
  displayName: initialDisplayName,
  classroomName: initialClassroom = 'AI & DS - A Section',
  onLogout,
}) => {
  const [username, setUsername] = useState<string>(initialUsername || (role === 'admin' ? 'admin' : 'aravind.k'));
  const [displayName, setDisplayName] = useState<string>(
    initialDisplayName || (role === 'admin' ? 'Dr. Raman S' : 'Mr. Aravind K')
  );
  const [userRole, setUserRole] = useState<string>(role);

  useEffect(() => {
    const loadInfo = async () => {
      const u = await StorageService.getUsername();
      const r = await StorageService.getRole();
      if (u) {
        setUsername(u);
        if (u.includes('.')) {
          const parts = u.split('.');
          const formatted = `${parts[0].charAt(0).toUpperCase() + parts[0].slice(1)} ${parts[1]?.toUpperCase() || ''}`.trim();
          setDisplayName(r === 'admin' ? `Dr. ${formatted}` : `Mr. ${formatted}`);
        }
      }
      if (r) setUserRole(r);
    };
    loadInfo();
  }, [role]);

  const initials = displayName
    .split(' ')
    .filter((_, i) => i > 0)
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase() || 'AK';

  const isTeacher = userRole === 'teacher';

  return (
    <View style={styles.container}>
      {/* Title */}
      <Text style={styles.title}>Profile</Text>

      {/* Main Profile Info */}
      <View style={styles.centerSection}>
        {/* Avatar */}
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{initials}</Text>
        </View>

        {/* Display Name */}
        <Text style={styles.nameText}>{displayName}</Text>

        {/* Role Badge */}
        <View style={styles.badgeContainer}>
          <StatusBadge status={isTeacher ? 'Teacher' : 'Admin'} size="sm" />
        </View>

        {/* Details Card */}
        <View style={styles.detailsCard}>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Username</Text>
            <Text style={styles.detailValue}>{username}</Text>
          </View>

          {isTeacher && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Classroom</Text>
              <Text style={styles.detailValue}>{initialClassroom}</Text>
            </View>
          )}

          {!isTeacher && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Access Level</Text>
              <Text style={styles.detailValue}>Full Administrator</Text>
            </View>
          )}
        </View>
      </View>

      {/* Log out Button matching UI design image */}
      <TouchableOpacity
        style={styles.logoutButton}
        onPress={onLogout}
        activeOpacity={0.7}
        accessibilityRole="button"
        accessibilityLabel="Log out"
      >
        <View style={styles.logoutLeft}>
          <LogOut size={18} color="#EF4444" strokeWidth={2.2} style={styles.logoutIcon} />
          <Text style={styles.logoutText}>Log out</Text>
        </View>
        <ChevronRight size={18} color="#EF4444" strokeWidth={2.2} />
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8FAFC',
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 24,
    justifyContent: 'space-between',
  },
  title: {
    fontSize: 20,
    fontWeight: '800',
    color: '#0F172A',
    marginBottom: 20,
  },
  centerSection: {
    alignItems: 'center',
    width: '100%',
  },
  avatar: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: '#EEF2FF',
    borderWidth: 3,
    borderColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 3,
    shadowColor: '#4F46E5',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.12,
    shadowRadius: 6,
    marginBottom: 14,
  },
  avatarText: {
    fontSize: 26,
    fontWeight: '800',
    color: '#4F46E5',
  },
  nameText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 8,
  },
  badgeContainer: {
    marginBottom: 28,
  },
  detailsCard: {
    width: '100%',
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: '#F1F5F9',
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.03,
    shadowRadius: 2,
  },
  detailRow: {
    paddingVertical: 12,
  },
  detailLabel: {
    fontSize: 12,
    color: '#64748B',
    fontWeight: '500',
    marginBottom: 2,
  },
  detailValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#FEF2F2',
    borderWidth: 1,
    borderColor: '#FEE2E2',
    borderRadius: 14,
    paddingVertical: 14,
    paddingHorizontal: 18,
    minHeight: 52,
  },
  logoutLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  logoutIcon: {
    marginRight: 10,
  },
  logoutText: {
    color: '#DC2626',
    fontWeight: '700',
    fontSize: 14.5,
  },
});
