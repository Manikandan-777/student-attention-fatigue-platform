/**
 * Alert Sound & Push Notification Settings Screen.
 *
 * Implements README_MOBILE_ALERT_NOTIFICATIONS.md §8.6:
 * - "Test alert sound" button (plays real level 4 sound tone).
 * - Per-level on/off toggles with design tokens.
 * - System notification settings link.
 * - Hardware volume, silent switch, and battery optimization guidance.
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Switch,
  Linking,
  Platform,
} from 'react-native';
import { THEME } from '../theme';
import { testAlertSound, NOTIFICATION_LEVELS } from '../services/notifications';

interface AlertSoundSettingsScreenProps {
  onBack?: () => void;
}

export const AlertSoundSettingsScreen: React.FC<AlertSoundSettingsScreenProps> = ({ onBack }) => {
  const [levelToggles, setLevelToggles] = useState<Record<string, boolean>>({
    'fatigue-l1-v1': true,
    'fatigue-l2-v1': true,
    'fatigue-l3-v1': true,
    'fatigue-l4-v1': true,
  });

  const [testPlaying, setTestPlaying] = useState(false);

  const handleTestSound = async () => {
    setTestPlaying(true);
    await testAlertSound();
    setTimeout(() => setTestPlaying(false), 2500);
  };

  const handleToggle = (id: string, value: boolean) => {
    setLevelToggles((prev) => ({ ...prev, [id]: value }));
  };

  const openSettings = () => {
    Linking.openSettings().catch(() => {});
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {onBack && (
        <TouchableOpacity
          style={styles.backButton}
          onPress={onBack}
          accessibilityRole="button"
          accessibilityLabel="Back to Profile"
        >
          <Text style={styles.backButtonIcon}>←</Text>
          <Text style={styles.backButtonText}>Back to Profile</Text>
        </TouchableOpacity>
      )}

      {/* Header Info */}
      <View style={styles.card}>
        <View style={styles.headerRow}>
          <Text style={styles.iconLarge}>🔊</Text>
          <Text style={styles.title}>Loud Alert Sound & Push</Text>
        </View>
        <Text style={styles.description}>
          High-priority notifications play an alarm-volume tone during classroom sessions to inform you of class fatigue trends.
        </Text>

        <TouchableOpacity
          style={[styles.testButton, testPlaying && styles.testButtonActive]}
          onPress={handleTestSound}
          activeOpacity={0.8}
          accessibilityRole="button"
          accessibilityLabel="Test Alert Sound"
        >
          <Text style={styles.testButtonIcon}>🔔</Text>
          <Text style={styles.testButtonText}>
            {testPlaying ? 'Playing Loud Alert...' : 'Test Alert Sound (Level 4)'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Per-Level Toggles */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Advisory Notification Levels</Text>
        <Text style={styles.sectionSubtitle}>
          Default is high sound enabled for all levels (conforming to specifications).
        </Text>

        {NOTIFICATION_LEVELS.map((level, idx) => (
          <View key={level.id} style={styles.levelRow}>
            <View style={styles.levelInfo}>
              <Text style={styles.levelName}>Level {idx + 1}: {level.name.split(':')[1] || level.name}</Text>
              <Text style={styles.levelDetails}>
                {level.bypassDnd ? 'High Priority • Breaks through DND' : 'Standard Priority • Max Volume'}
              </Text>
            </View>
            <Switch
              value={levelToggles[level.id] ?? true}
              onValueChange={(val) => handleToggle(level.id, val)}
              trackColor={{ false: THEME.colors.borderSubtle, true: THEME.colors.accentPrimary }}
              thumbColor="#FFFFFF"
            />
          </View>
        ))}
      </View>

      {/* Hardware & System Guidance */}
      <View style={styles.card}>
        <View style={styles.headerRow}>
          <Text style={styles.iconMed}>🛡️</Text>
          <Text style={styles.sectionTitle}>Audio & Device Optimization Tips</Text>
        </View>

        <View style={styles.tipItem}>
          <Text style={styles.tipBullet}>•</Text>
          <Text style={styles.tipText}>
            <Text style={styles.boldText}>Volume Settings: </Text>
            Turn up the Alarm and Notification volume streams in your device settings.
          </Text>
        </View>

        <View style={styles.tipItem}>
          <Text style={styles.tipBullet}>•</Text>
          <Text style={styles.tipText}>
            <Text style={styles.boldText}>Silent Mode: </Text>
            {Platform.OS === 'ios'
              ? 'On iPhone, the physical silent switch mutes sounds. Switch off silent mode for audible alarms.'
              : 'On Android, the alarm channel will play at alarm volume unless the alarm stream is fully muted.'}
          </Text>
        </View>

        <View style={styles.tipItem}>
          <Text style={styles.tipBullet}>•</Text>
          <Text style={styles.tipText}>
            <Text style={styles.boldText}>Battery Optimization: </Text>
            If background alerts arrive late, disable battery optimization for this application.
          </Text>
        </View>

        <TouchableOpacity
          style={styles.settingsLinkButton}
          onPress={openSettings}
          accessibilityRole="button"
          accessibilityLabel="Open System Notification Settings"
        >
          <Text style={styles.settingsLinkIcon}>⚙️</Text>
          <Text style={styles.settingsLinkText}>Open System Notification Settings</Text>
        </TouchableOpacity>
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
    gap: THEME.spacing.space6,
  },
  card: {
    backgroundColor: THEME.colors.bgSurface,
    borderRadius: THEME.radius.xl,
    padding: THEME.spacing.space8,
    borderWidth: 1,
    borderColor: THEME.colors.borderSubtle,
    marginBottom: THEME.spacing.space6,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: THEME.spacing.space4,
  },
  iconLarge: {
    fontSize: 22,
    marginRight: THEME.spacing.space4,
  },
  iconMed: {
    fontSize: 18,
    marginRight: THEME.spacing.space3,
  },
  title: {
    fontSize: THEME.typography.sizes.lg,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
  },
  description: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.textSecondary,
    lineHeight: 20,
    marginBottom: THEME.spacing.space6,
  },
  testButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: THEME.colors.accentPrimary,
    borderRadius: THEME.radius.lg,
    paddingVertical: THEME.spacing.space4,
    paddingHorizontal: THEME.spacing.space6,
    minHeight: THEME.spacing.space11,
  },
  testButtonActive: {
    backgroundColor: THEME.colors.accentDanger,
  },
  testButtonIcon: {
    fontSize: 18,
    marginRight: THEME.spacing.space3,
    color: '#FFFFFF',
  },
  testButtonText: {
    color: '#FFFFFF',
    fontSize: THEME.typography.sizes.sm,
    fontWeight: '600',
  },
  sectionTitle: {
    fontSize: THEME.typography.sizes.base,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
    marginBottom: THEME.spacing.space1,
  },
  sectionSubtitle: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textSecondary,
    marginBottom: THEME.spacing.space4,
  },
  levelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: THEME.spacing.space4,
    borderBottomWidth: 1,
    borderBottomColor: THEME.colors.borderSubtle,
  },
  levelInfo: {
    flex: 1,
    marginRight: THEME.spacing.space4,
  },
  levelName: {
    fontSize: THEME.typography.sizes.sm,
    fontWeight: '600',
    color: THEME.colors.textPrimary,
    textTransform: 'capitalize',
  },
  levelDetails: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textMuted,
    marginTop: 2,
  },
  tipItem: {
    flexDirection: 'row',
    marginTop: THEME.spacing.space3,
  },
  tipBullet: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.accentPrimary,
    marginRight: 6,
  },
  tipText: {
    flex: 1,
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textSecondary,
    lineHeight: 18,
  },
  boldText: {
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
  },
  settingsLinkButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: THEME.spacing.space6,
    paddingVertical: THEME.spacing.space3,
    minHeight: THEME.spacing.space11,
  },
  settingsLinkIcon: {
    fontSize: 16,
    marginRight: THEME.spacing.space2,
  },
  settingsLinkText: {
    color: THEME.colors.accentPrimary,
    fontSize: THEME.typography.sizes.sm,
    fontWeight: '600',
  },
  backButton: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: THEME.spacing.space4,
    paddingVertical: THEME.spacing.space2,
    minHeight: THEME.spacing.space11,
  },
  backButtonIcon: {
    fontSize: 20,
    color: THEME.colors.accentPrimary,
    marginRight: THEME.spacing.space2,
    fontWeight: 'bold',
  },
  backButtonText: {
    color: THEME.colors.accentPrimary,
    fontSize: THEME.typography.sizes.sm,
    fontWeight: '600',
  },
});
