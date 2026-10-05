import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { CalendarClock } from 'lucide-react-native';
import { THEME } from '../theme';

interface EmptySessionStateProps {
  message?: string;
  subtext?: string;
}

export const EmptySessionState: React.FC<EmptySessionStateProps> = ({
  message = 'No class is being monitored right now.',
  subtext = 'Start a class session to see live data here.',
}) => {
  return (
    <View style={styles.container}>
      <View style={styles.iconCircle}>
        <CalendarClock size={52} color="#93C5FD" strokeWidth={1.5} />
      </View>
      <Text style={styles.title}>{message}</Text>
      <Text style={styles.subtext}>{subtext}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
    paddingHorizontal: 24,
  },
  iconCircle: {
    width: 90,
    height: 90,
    borderRadius: 45,
    backgroundColor: '#EFF6FF',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0F172A',
    textAlign: 'center',
    marginBottom: 6,
  },
  subtext: {
    fontSize: 13,
    color: '#64748B',
    textAlign: 'center',
    lineHeight: 18,
  },
});
