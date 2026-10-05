import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { CloudOff } from 'lucide-react-native';
import { THEME } from '../theme';

interface OfflineStateProps {
  onRetry?: () => void;
}

export const OfflineState: React.FC<OfflineStateProps> = ({ onRetry }) => {
  return (
    <View style={styles.card}>
      <View style={styles.iconCircle}>
        <CloudOff size={48} color="#A5B4FC" strokeWidth={1.6} />
      </View>
      <Text style={styles.title}>Showing the latest available data.</Text>
      <Text style={styles.subtext}>
        Realtime updates are currently unavailable. We will reconnect automatically.
      </Text>
      {onRetry && (
        <TouchableOpacity
          onPress={onRetry}
          style={styles.retryButton}
          activeOpacity={0.8}
          accessibilityRole="button"
          accessibilityLabel="Retry Now"
        >
          <Text style={styles.retryText}>Retry Now</Text>
        </TouchableOpacity>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 16,
    borderWidth: 1,
    borderColor: '#F1F5F9',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
  },
  iconCircle: {
    width: 84,
    height: 84,
    borderRadius: 42,
    backgroundColor: '#EEF2FF',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 15,
    fontWeight: '700',
    color: '#0F172A',
    textAlign: 'center',
    marginBottom: 6,
  },
  subtext: {
    fontSize: 12.5,
    color: '#64748B',
    textAlign: 'center',
    lineHeight: 18,
    marginBottom: 20,
    paddingHorizontal: 12,
  },
  retryButton: {
    backgroundColor: '#4F46E5',
    borderRadius: 14,
    paddingVertical: 12,
    paddingHorizontal: 32,
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 160,
  },
  retryText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
  },
});
