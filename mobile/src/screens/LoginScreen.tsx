import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { THEME } from '../theme';
import { ApiService } from '../services/api';
import { StorageService } from '../services/storage';

interface LoginScreenProps {
  onLoginSuccess: (role: string) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleLogin = async () => {
    if (!username.trim() || !password.trim()) {
      setErrorMessage('Invalid username or password.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    try {
      const data = await ApiService.login(username.trim(), password.trim());
      await StorageService.saveAuth(data.access_token, data.role, username.trim());
      onLoginSuccess(data.role);
    } catch (err: any) {
      if (err?.response?.data?.detail?.message) {
        setErrorMessage(err.response.data.detail.message);
      } else if (err?.message && (err.message.includes('Network Error') || err.message.includes('timeout'))) {
        setErrorMessage('Cannot reach backend server. Check network connection.');
      } else {
        // Per APP-25 default fallback
        setErrorMessage('Invalid username or password.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.appTitle}>AI MONITOR</Text>
        <Text style={styles.subTitle}>Classroom Attention & Fatigue System</Text>

        {errorMessage && (
          <View
            accessibilityRole="alert"
            style={styles.errorContainer}
          >
            <Text style={styles.errorText}>{errorMessage}</Text>
          </View>
        )}

        <View style={styles.fieldContainer}>
          <Text style={styles.label}>Email / Username</Text>
          <TextInput
            value={username}
            onChangeText={setUsername}
            autoCapitalize="none"
            placeholder="teacher_1 or admin"
            placeholderTextColor={THEME.colors.textMuted}
            style={styles.input}
            accessibilityLabel="Email / Username"
          />
        </View>

        <View style={styles.fieldContainer}>
          <Text style={styles.label}>Password</Text>
          <TextInput
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            placeholder="••••••••"
            placeholderTextColor={THEME.colors.textMuted}
            style={styles.input}
            accessibilityLabel="Password"
          />
        </View>

        <TouchableOpacity
          onPress={handleLogin}
          disabled={loading}
          activeOpacity={0.8}
          accessibilityRole="button"
          accessibilityLabel="LOGIN"
          style={styles.loginButton}
        >
          {loading ? (
            <ActivityIndicator color={THEME.colors.bgSurface} />
          ) : (
            <Text style={styles.loginButtonText}>LOGIN</Text>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME.colors.bgApp,
    justifyContent: 'center',
    padding: THEME.spacing.space10,
  },
  card: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    borderRadius: THEME.radius.xl,
    padding: THEME.spacing.space10,
  },
  appTitle: {
    fontSize: THEME.typography.sizes.xl,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
    textAlign: 'center',
    marginBottom: THEME.spacing.space2,
  },
  subTitle: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textSecondary,
    textAlign: 'center',
    marginBottom: THEME.spacing.space10,
  },
  errorContainer: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.accentDanger,
    borderWidth: 1,
    borderRadius: THEME.radius.lg,
    padding: THEME.spacing.space4,
    marginBottom: THEME.spacing.space6,
  },
  errorText: {
    color: THEME.colors.accentDanger,
    fontSize: THEME.typography.sizes.xs,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  fieldContainer: {
    marginBottom: THEME.spacing.space6,
  },
  label: {
    fontSize: THEME.typography.sizes.sm,
    fontWeight: '600',
    color: THEME.colors.textBody,
    marginBottom: THEME.spacing.space2,
  },
  input: {
    minHeight: THEME.spacing.space11, // 44dp touch target
    borderWidth: 1,
    borderColor: THEME.colors.borderStrong,
    borderRadius: THEME.radius.lg,
    paddingHorizontal: THEME.spacing.space6,
    fontSize: THEME.typography.sizes.base,
    color: THEME.colors.textPrimary,
    backgroundColor: THEME.colors.bgSurface,
  },
  loginButton: {
    minHeight: THEME.spacing.space11, // 44dp touch target
    backgroundColor: THEME.colors.accentPrimary,
    borderRadius: THEME.radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: THEME.spacing.space4,
  },
  loginButtonText: {
    color: THEME.colors.bgSurface,
    fontWeight: 'bold',
    fontSize: THEME.typography.sizes.base,
  },
});
