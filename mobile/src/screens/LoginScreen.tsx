import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { User, Lock, Eye, EyeOff, AlertCircle, GraduationCap } from 'lucide-react-native';
import Svg, { Path } from 'react-native-svg';
import { THEME } from '../theme';
import { ApiService } from '../services/api';
import { StorageService } from '../services/storage';
import { soundAlertService } from '../services/soundAlert';

interface LoginScreenProps {
  onLoginSuccess: (role: string, username?: string) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
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
      soundAlertService.unlockAudio();
      const data = await ApiService.login(username.trim(), password.trim());
      await StorageService.saveAuth(data.access_token, data.role, username.trim());
      onLoginSuccess(data.role, username.trim());
    } catch (err: any) {
      // Per spec: "Wrong login: Show 'Invalid username or password.' (same message for a wrong user or wrong password)"
      setErrorMessage('Invalid username or password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={styles.keyboardContainer}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {/* App Logo & Title */}
        <View style={styles.header}>
          <View style={styles.logoBadge}>
            <GraduationCap size={44} color="#4F46E5" strokeWidth={1.8} />
          </View>
          <Text style={styles.appTitle}>AI Classroom Monitor</Text>
          <Text style={styles.appSubtitle}>Student Attention & Fatigue Detection</Text>
        </View>

        {/* Welcome Section */}
        <View style={styles.formSection}>
          <Text style={styles.welcomeTitle}>Welcome back</Text>
          <Text style={styles.welcomeSubtitle}>Please login to continue</Text>

          {/* Username Input */}
          <View style={styles.inputContainer}>
            <User size={18} color="#94A3B8" style={styles.inputIcon} />
            <TextInput
              value={username}
              onChangeText={(text) => {
                setUsername(text);
                if (errorMessage) setErrorMessage(null);
              }}
              autoCapitalize="none"
              autoCorrect={false}
              placeholder="Username"
              placeholderTextColor="#94A3B8"
              style={styles.input}
              accessibilityLabel="Username"
            />
          </View>

          {/* Password Input */}
          <View style={styles.inputContainer}>
            <Lock size={18} color="#94A3B8" style={styles.inputIcon} />
            <TextInput
              value={password}
              onChangeText={(text) => {
                setPassword(text);
                if (errorMessage) setErrorMessage(null);
              }}
              secureTextEntry={!showPassword}
              placeholder="Password"
              placeholderTextColor="#94A3B8"
              style={styles.input}
              accessibilityLabel="Password"
            />
            <TouchableOpacity
              onPress={() => setShowPassword(!showPassword)}
              hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
              accessibilityRole="button"
              accessibilityLabel={showPassword ? 'Hide password' : 'Show password'}
              style={styles.eyeIcon}
            >
              {showPassword ? (
                <EyeOff size={18} color="#94A3B8" />
              ) : (
                <Eye size={18} color="#94A3B8" />
              )}
            </TouchableOpacity>
          </View>

          {/* Login Button */}
          <TouchableOpacity
            onPress={handleLogin}
            disabled={loading}
            activeOpacity={0.8}
            accessibilityRole="button"
            accessibilityLabel="Login"
            style={styles.loginButton}
          >
            {loading ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.loginButtonText}>Login</Text>
            )}
          </TouchableOpacity>

          {/* Error Message */}
          {errorMessage ? (
            <View
              accessibilityRole="alert"
              style={styles.errorContainer}
            >
              <AlertCircle size={14} color="#DC2626" style={styles.errorIcon} />
              <Text style={styles.errorText}>{errorMessage}</Text>
            </View>
          ) : null}
        </View>

        {/* Decorative Wave at Bottom */}
        <View style={styles.bottomWaveContainer} pointerEvents="none">
          <Svg width="100%" height={100} viewBox="0 0 375 100" preserveAspectRatio="none">
            <Path
              d="M0 40 C 120 80, 240 10, 375 50 L 375 100 L 0 100 Z"
              fill="#EDE9FE"
              opacity={0.45}
            />
            <Path
              d="M0 60 C 100 20, 260 90, 375 40 L 375 100 L 0 100 Z"
              fill="#DDD6FE"
              opacity={0.35}
            />
          </Svg>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  keyboardContainer: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'space-between',
    paddingHorizontal: 28,
    paddingTop: 50,
  },
  header: {
    alignItems: 'center',
    marginTop: 20,
    marginBottom: 28,
  },
  logoBadge: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#EEF2FF',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  appTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: '#0F172A',
    letterSpacing: -0.3,
  },
  appSubtitle: {
    fontSize: 12.5,
    color: '#64748B',
    marginTop: 4,
    fontWeight: '500',
  },
  formSection: {
    width: '100%',
    paddingBottom: 20,
  },
  welcomeTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 3,
  },
  welcomeSubtitle: {
    fontSize: 13,
    color: '#64748B',
    marginBottom: 20,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F8FAFC',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    paddingHorizontal: 14,
    minHeight: 52,
    marginBottom: 14,
  },
  inputIcon: {
    marginRight: 10,
  },
  input: {
    flex: 1,
    fontSize: 15,
    color: '#0F172A',
    paddingVertical: 10,
  },
  eyeIcon: {
    padding: 6,
  },
  loginButton: {
    backgroundColor: '#4F46E5',
    borderRadius: 14,
    minHeight: 52,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 6,
    elevation: 3,
    shadowColor: '#4F46E5',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 6,
  },
  loginButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  errorContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 14,
  },
  errorIcon: {
    marginRight: 6,
  },
  errorText: {
    color: '#DC2626',
    fontSize: 13,
    fontWeight: '600',
  },
  bottomWaveContainer: {
    width: '100%',
    marginTop: 20,
  },
});
