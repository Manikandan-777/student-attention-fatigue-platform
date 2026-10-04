import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, StyleSheet } from 'react-native';
import { THEME } from '../theme';
import { StudentItem } from '../components/StudentItem';
import { mobileTelemetry } from '../services/websocket';
import { TrackResultLite } from '../types';

interface StudentListScreenProps {
  onSelectStudent: (student: TrackResultLite) => void;
}

export const StudentListScreen: React.FC<StudentListScreenProps> = ({
  onSelectStudent,
}) => {
  const [students, setStudents] = useState<TrackResultLite[]>([]);

  useEffect(() => {
    // Initial sample fallback tracks
    const unsub = mobileTelemetry.onTelemetry((data) => {
      if (data.tracks && data.tracks.length > 0) {
        setStudents(data.tracks);
      }
    });

    return () => unsub();
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Monitored Students ({students.length})</Text>

      {students.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>No students currently detected.</Text>
          <Text style={styles.emptySubtext}>
            Detected students will automatically appear here once tracking commences.
          </Text>
        </View>
      ) : (
        <FlatList
          data={students}
          keyExtractor={(item) => item.track_id.toString()}
          renderItem={({ item }) => (
            <StudentItem
              student={item}
              onPress={() => onSelectStudent(item)}
            />
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
  emptyContainer: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    borderRadius: THEME.radius.xl,
    padding: THEME.spacing.space12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyText: {
    fontSize: THEME.typography.sizes.base,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
    marginBottom: THEME.spacing.space2,
  },
  emptySubtext: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textSecondary,
    textAlign: 'center',
  },
});
