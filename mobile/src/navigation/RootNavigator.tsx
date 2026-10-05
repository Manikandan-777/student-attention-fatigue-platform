import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { THEME } from '../theme';
import { StorageService } from '../services/storage';
import { LoginScreen } from '../screens/LoginScreen';

// Teacher Screens
import { TeacherDashboardScreen } from '../screens/TeacherDashboardScreen';
import { StudentListScreen } from '../screens/StudentListScreen';
import { StudentDetailScreen } from '../screens/StudentDetailScreen';
import { AlertCenterScreen } from '../screens/AlertCenterScreen';
import { SessionReportScreen } from '../screens/SessionReportScreen';
import { TeacherProfileScreen } from '../screens/TeacherProfileScreen';
import { AlertSoundSettingsScreen } from '../screens/AlertSoundSettingsScreen';

// Admin Screens
import { AdminDashboardScreen } from '../screens/AdminDashboardScreen';
import { ManageStudentsScreen } from '../screens/ManageStudentsScreen';
import { ManageTeachersScreen } from '../screens/ManageTeachersScreen';
import { ManageClassroomsScreen } from '../screens/ManageClassroomsScreen';
import { SystemStatusScreen } from '../screens/SystemStatusScreen';

import { TrackResultLite } from '../types';

export const RootNavigator: React.FC = () => {
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Active navigation tab
  const [activeTab, setActiveTab] = useState<string>('Dashboard');
  const [selectedStudent, setSelectedStudent] = useState<TrackResultLite | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      const storedToken = await StorageService.getToken();
      const storedRole = await StorageService.getRole();
      setToken(storedToken);
      setRole(storedRole);
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const handleLoginSuccess = (userRole: string) => {
    setToken('authenticated');
    setRole(userRole);
    setActiveTab('Dashboard');
    setSelectedStudent(null);
  };

  const handleLogout = () => {
    setToken(null);
    setRole(null);
    setActiveTab('Dashboard');
    setSelectedStudent(null);
  };

  if (isLoading) {
    return (
      <View style={styles.center}>
        <Text style={styles.loadingText}>Initializing ClassAware...</Text>
      </View>
    );
  }

  if (!token) {
    return <LoginScreen onLoginSuccess={handleLoginSuccess} />;
  }

  // Teacher Tabs per APP-22
  const teacherTabs = [
    { name: 'Dashboard', label: 'Dashboard' },
    { name: 'Students', label: 'Students' },
    { name: 'Alerts', label: 'Alerts' },
    { name: 'Reports', label: 'Reports' },
    { name: 'Profile', label: 'Profile' },
  ];

  // Admin Tabs per APP-22
  const adminTabs = [
    { name: 'Dashboard', label: 'Dashboard' },
    { name: 'Students', label: 'Students' },
    { name: 'Teachers', label: 'Teachers' },
    { name: 'Classrooms', label: 'Classrooms' },
    { name: 'Status', label: 'Status' },
    { name: 'Profile', label: 'Profile' },
  ];

  const currentTabs = role === 'admin' ? adminTabs : teacherTabs;

  const renderTeacherContent = () => {
    if (selectedStudent) {
      return (
        <StudentDetailScreen
          student={selectedStudent}
          onBack={() => setSelectedStudent(null)}
          onViewReport={() => {
            setSelectedStudent(null);
            setActiveTab('Reports');
          }}
        />
      );
    }

    switch (activeTab) {
      case 'Dashboard':
        return (
          <TeacherDashboardScreen
            onNavigate={(screen) => setActiveTab(screen)}
          />
        );
      case 'Students':
        return (
          <StudentListScreen
            onSelectStudent={(st) => setSelectedStudent(st)}
          />
        );
      case 'Alerts':
        return <AlertCenterScreen />;
      case 'Reports':
        return <SessionReportScreen />;
      case 'AlertSound':
        return <AlertSoundSettingsScreen onBack={() => setActiveTab('Profile')} />;
      case 'Profile':
      default:
        return (
          <TeacherProfileScreen
            onLogout={handleLogout}
            onNavigateSettings={() => setActiveTab('AlertSound')}
          />
        );
    }
  };

  const renderAdminContent = () => {
    switch (activeTab) {
      case 'Dashboard':
        return <AdminDashboardScreen />;
      case 'Students':
        return <ManageStudentsScreen />;
      case 'Teachers':
        return <ManageTeachersScreen />;
      case 'Classrooms':
        return <ManageClassroomsScreen />;
      case 'Status':
        return <SystemStatusScreen />;
      case 'AlertSound':
        return <AlertSoundSettingsScreen onBack={() => setActiveTab('Profile')} />;
      case 'Profile':
      default:
        return (
          <TeacherProfileScreen
            onLogout={handleLogout}
            onNavigateSettings={() => setActiveTab('AlertSound')}
          />
        );
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.body}>
        {role === 'admin' ? renderAdminContent() : renderTeacherContent()}
      </View>

      {/* Bottom Tab Bar per APP-22 */}
      <View
        accessibilityRole="tablist"
        aria-label="Bottom navigation tabs"
        style={styles.tabBar}
      >
        {currentTabs.map((tab) => (
          <TouchableOpacity
            key={tab.name}
            style={styles.tabItem}
            onPress={() => {
              setSelectedStudent(null);
              setActiveTab(tab.name);
            }}
            accessibilityRole="tab"
            accessibilityState={{ selected: activeTab === tab.name && !selectedStudent }}
            accessibilityLabel={tab.label}
          >
            <Text
              style={[
                styles.tabLabel,
                activeTab === tab.name && !selectedStudent && styles.tabLabelActive,
              ]}
            >
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    height: '100%',
    minHeight: '100%',
    backgroundColor: THEME.colors.bgSurface,
  },
  body: {
    flex: 1,
    height: '100%',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: THEME.colors.bgApp,
  },
  loadingText: {
    fontSize: THEME.typography.sizes.base,
    color: THEME.colors.textSecondary,
  },
  tabBar: {
    minHeight: THEME.spacing.space13, // 56dp per UI-2 space-13
    flexDirection: 'row',
    borderTopWidth: 1,
    borderTopColor: THEME.colors.borderSubtle,
    backgroundColor: THEME.colors.bgSurface,
    alignItems: 'center',
  },
  tabItem: {
    flex: 1,
    minHeight: THEME.spacing.space11, // 44dp touch target per UI-7
    justifyContent: 'center',
    alignItems: 'center',
  },
  tabLabel: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textSecondary,
    fontWeight: '600',
  },
  tabLabelActive: {
    color: THEME.colors.accentPrimary,
    fontWeight: 'bold',
  },
});
