import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import { THEME } from '../theme';
import { StatusBadge } from '../components/StatusBadge';
import { ApiService } from '../services/api';
import { Classroom } from '../types';

export const ManageClassroomsScreen: React.FC = () => {
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadClassrooms = async () => {
      try {
        const data = await ApiService.getClassrooms();
        setClassrooms(data);
      } catch {
        // fallback
      } finally {
        setLoading(false);
      }
    };
    loadClassrooms();
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Classroom Management</Text>

      {loading ? (
        <ActivityIndicator color={THEME.colors.accentPrimary} />
      ) : (
        <FlatList
          data={classrooms}
          keyExtractor={(item) => item.id.toString()}
          renderItem={({ item }) => (
            <View style={styles.card}>
              <View style={styles.headerRow}>
                <Text style={styles.title}>{item.name}</Text>
                <StatusBadge status={item.is_active ? 'Online' : 'Offline'} size="sm" />
              </View>

              <View style={styles.divider} />

              <View style={styles.infoRow}>
                <Text style={styles.label}>Camera ID:</Text>
                <Text style={styles.value}>{item.camera_id}</Text>
              </View>

              <View style={styles.infoRow}>
                <Text style={styles.label}>Status:</Text>
                <Text style={styles.value}>{item.is_active ? 'Active' : 'Inactive'}</Text>
              </View>
            </View>
          )}
          contentContainerStyle={styles.listContent}
        />
      )}
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
  listContent: {
    paddingBottom: THEME.spacing.space10,
  },
  card: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    borderRadius: THEME.radius.xl,
    padding: THEME.spacing.space8,
    marginBottom: THEME.spacing.space4,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    fontSize: THEME.typography.sizes.base,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
  },
  divider: {
    height: 1,
    backgroundColor: THEME.colors.borderSubtle,
    marginVertical: THEME.spacing.space3,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: THEME.spacing.space1,
  },
  label: {
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.textSecondary,
  },
  value: {
    fontSize: THEME.typography.sizes.sm,
    fontWeight: '600',
    color: THEME.colors.textPrimary,
  },
});
