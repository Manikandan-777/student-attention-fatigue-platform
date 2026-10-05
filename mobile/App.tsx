import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { RootNavigator } from './src/navigation/RootNavigator';
import { ErrorBoundary } from './src/components/ErrorBoundary';

export default function App() {
  return (
    <SafeAreaProvider style={{ flex: 1 }}>
      <ErrorBoundary>
        <StatusBar style="auto" />
        <RootNavigator />
      </ErrorBoundary>
    </SafeAreaProvider>
  );
}
