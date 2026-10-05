import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LayoutDashboard, Users, User } from 'lucide-react-native';
import { THEME } from '../theme';
import { StorageService } from '../services/storage';
import { ApiService } from '../services/api';
import { WebSocketService } from '../services/websocket';
import { LoginScreen } from '../screens/LoginScreen';
import { TeacherDashboardScreen } from '../screens/TeacherDashboardScreen';
import { AdminDashboardScreen } from '../screens/AdminDashboardScreen';
import { ManageTeachersScreen } from '../screens/ManageTeachersScreen';
import { TeacherProfileScreen } from '../screens/TeacherProfileScreen';

export const RootNavigator: React.FC = () => {
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [userProfile, setUserProfile] = useState<{ username: string; display_name?: string } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<string>('Dashboard');

  useEffect(() => {
    const checkAuth = async () => {
      const storedToken = await StorageService.getToken();
      const storedRole = await StorageService.getRole();
      setToken(storedToken);
      setRole(storedRole);

      if (storedToken) {
        try {
          const me = await ApiService.getMe();
          setUserProfile({ username: me.username });
        } catch {
          // If token expired, logout cleanly
          await StorageService.clearAll();
          setToken(null);
          setRole(null);
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const handleLoginSuccess = async (userRole: string, username?: string) => {
    setToken('authenticated');
    setRole(userRole);
    if (username) {
      setUserProfile({ username });
    } else {
      try {
        const me = await ApiService.getMe();
        setUserProfile({ username: me.username });
      } catch {
        // Fallback
      }
    }
    setActiveTab('Dashboard');
  };

  const handleLogout = async () => {
    try {
      await ApiService.logout();
    } catch {
      // Ignore
    }
    WebSocketService.disconnect();
    await StorageService.clearAll();
    setToken(null);
    setRole(null);
    setUserProfile(null);
    setActiveTab('Dashboard');
  };

  if (isLoading) {
    return (
      <View style={styles.center}>
        <Text style={styles.loadingText}>Initializing AI Classroom Monitor...</Text>
      </View>
    );
  }

  if (!token) {
    return <LoginScreen onLoginSuccess={handleLoginSuccess} />;
  }

  // Teacher Tabs per §2: Dashboard, Profile
  const teacherTabs = [
    { name: 'Dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { name: 'Profile', label: 'Profile', icon: User },
  ];

  // Admin Tabs per §2: Dashboard, Teachers, Profile
  const adminTabs = [
    { name: 'Dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { name: 'Teachers', label: 'Teachers', icon: Users },
    { name: 'Profile', label: 'Profile', icon: User },
  ];

  const currentTabs = role === 'admin' ? adminTabs : teacherTabs;

  const renderContent = () => {
    if (role === 'admin') {
      switch (activeTab) {
        case 'Dashboard':
          return <AdminDashboardScreen onNavigateTab={(tab) => setActiveTab(tab)} />;
        case 'Teachers':
          return <ManageTeachersScreen />;
        case 'Profile':
        default:
          return (
            <TeacherProfileScreen
              role="admin"
              username={userProfile?.username || 'admin'}
              displayName="Dr. Raman S"
              onLogout={handleLogout}
            />
          );
      }
    } else {
      switch (activeTab) {
        case 'Dashboard':
          return <TeacherDashboardScreen onNavigateTab={(tab) => setActiveTab(tab)} />;
        case 'Profile':
        default:
          return (
            <TeacherProfileScreen
              role="teacher"
              username={userProfile?.username || 'aravind.k'}
              displayName="Mr. Aravind K"
              classroomName="AI & DS - A Section"
              onLogout={handleLogout}
            />
          );
      }
    }
  };

  return (
    <SafeAreaView style={styles.safeArea} edges={['top', 'bottom', 'left', 'right']}>
      <View style={styles.body}>{renderContent()}</View>

      {/* Bottom Tab Bar matching Exact UI design */}
      <View
        accessibilityRole="tablist"
        aria-label="Bottom navigation tabs"
        style={styles.tabBar}
      >
        {currentTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.name;
          return (
            <TouchableOpacity
              key={tab.name}
              style={styles.tabItem}
              onPress={() => setActiveTab(tab.name)}
              accessibilityRole="tab"
              accessibilityState={{ selected: isActive }}
              accessibilityLabel={tab.label}
              activeOpacity={0.7}
            >
              <Icon
                size={22}
                color={isActive ? THEME.colors.primary : THEME.colors.textMuted}
                strokeWidth={isActive ? 2.4 : 1.8}
              />
              <Text
                style={[
                  styles.tabLabel,
                  isActive && styles.tabLabelActive,
                ]}
              >
                {tab.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    height: '100%',
    minHeight: '100%',
    backgroundColor: THEME.colors.background,
  },
  body: {
    flex: 1,
    height: '100%',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: THEME.colors.background,
  },
  loadingText: {
    fontSize: 15,
    color: THEME.colors.textSecondary,
    fontWeight: '500',
  },
  tabBar: {
    minHeight: 58,
    flexDirection: 'row',
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    paddingBottom: 2,
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.04,
    shadowRadius: 3,
  },
  tabItem: {
    flex: 1,
    minHeight: 48,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 4,
  },
  tabLabel: {
    fontSize: 11,
    color: THEME.colors.textMuted,
    fontWeight: '500',
    marginTop: 2,
  },
  tabLabelActive: {
    color: THEME.colors.primary,
    fontWeight: '700',
  },
});
