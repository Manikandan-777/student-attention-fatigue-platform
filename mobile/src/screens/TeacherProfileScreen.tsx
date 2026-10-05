import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { THEME } from '../theme';
import { StorageService } from '../services/storage';

interface TeacherProfileScreenProps {
  onLogout: () => void;
  onNavigateSettings?: () => void;
}

export const TeacherProfileScreen: React.FC<TeacherProfileScreenProps> = ({ onLogout, onNavigateSettings }) => {
  const [username, setUsername] = useState<string>('Teacher');
  const [role, setRole] = useState<string>('teacher');

  useEffect(() => {
    const loadInfo = async () => {
      const u = await StorageService.getUsername();
      const r = await StorageService.getRole();
      if (u) setUsername(u);
      if (r) setRole(r);
    };
    loadInfo();
  }, []);

  const handleLogout = async () => {
    try {
      const { unregisterPush } = await import('../services/notifications');
      await unregisterPush();
    } catch {
      // ignore
    }
    await StorageService.clearAuth();
    onLogout();
  };

  return (
    <View style={styles.container}>
      <Text style={styles.header}>User Profile</Text>

      <View style={styles.card}>
        <View style={styles.infoRow}>
          <Text style={styles.label}>Username</Text>
          <Text style={styles.value}>{username}</Text>
        </View>

        <View style={styles.divider} />

        <View style={styles.infoRow}>
          <Text style={styles.label}>Role</Text>
          <Text style={[styles.value, styles.roleValue]}>{role}</Text>
        </View>

        <View style={styles.divider} />

        <View style={styles.infoRow}>
          <Text style={styles.label}>Application</Text>
          <Text style={styles.value}>ClassAware Mobile</Text>
        </View>

        {onNavigateSettings && (
          <>
            <View style={styles.divider} />
            <TouchableOpacity
              style={styles.settingsRow}
              onPress={onNavigateSettings}
              accessibilityRole="button"
              accessibilityLabel="Alert Sound Settings"
            >
              <Text style={styles.settingsLabel}>Alert Sound & Push Notifications</Text>
              <Text style={styles.settingsChevron}>›</Text>
            </TouchableOpacity>
          </>
        )}
      </View>

      <TouchableOpacity
        style={styles.logoutButton}
        onPress={handleLogout}
        accessibilityRole="button"
        accessibilityLabel="Log Out"
      >
        <Text style={styles.logoutButtonText}>Log Out</Text>
      </TouchableOpacity>
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
  card: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    borderRadius: THEME.radius.xl,
    padding: THEME.spacing.space8,
    marginBottom: THEME.spacing.space8,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: THEME.spacing.space2,
  },
  label: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.textSecondary,
  },
  value: {
    fontSize: THEME.typography.sizes.sm,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
  },
  roleValue: {
    textTransform: 'capitalize',
    color: THEME.colors.accentPrimary,
  },
  divider: {
    height: 1,
    backgroundColor: THEME.colors.borderSubtle,
    marginVertical: THEME.spacing.space3,
  },
  logoutButton: {
    minHeight: THEME.spacing.space11, // 44dp
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.accentDanger,
    borderWidth: 1,
    borderRadius: THEME.radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoutButtonText: {
    color: THEME.colors.accentDanger,
    fontWeight: 'bold',
    fontSize: THEME.typography.sizes.base,
  },
  settingsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: THEME.spacing.space3,
    minHeight: THEME.spacing.space11, // 44dp
  },
  settingsLabel: {
    fontSize: THEME.typography.sizes.sm,
    fontWeight: '600',
    color: THEME.colors.accentPrimary,
  },
  settingsChevron: {
    fontSize: THEME.typography.sizes.lg,
    color: THEME.colors.textSecondary,
    fontWeight: 'bold',
  },
});
