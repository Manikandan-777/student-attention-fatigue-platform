import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
} from 'react-native';
import { THEME } from '../theme';
import { ApiService } from '../services/api';
import { Student } from '../types';

export const ManageStudentsScreen: React.FC = () => {
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [studentId, setStudentId] = useState('');
  const [name, setName] = useState('');
  const [department, setDepartment] = useState('AI & DS');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchStudents = async () => {
    setLoading(true);
    try {
      const data = await ApiService.getStudents();
      setStudents(data);
    } catch {
      // offline fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, []);

  const handleAddStudent = async () => {
    if (!studentId.trim() || !name.trim()) {
      setErrorMessage('Student ID and Name are required.');
      return;
    }

    setErrorMessage(null);
    try {
      const newSt = await ApiService.createStudent({
        student_id: studentId.trim(),
        name: name.trim(),
        department: department.trim(),
        year: 3,
        section: 'A',
      });
      setStudents((prev) => [...prev, newSt]);
      setStudentId('');
      setName('');
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setErrorMessage(error.response?.data?.detail ?? 'Failed to create student.');
    }
  };

  const handleDeactivate = async (id: number) => {
    try {
      await ApiService.deactivateStudent(id);
      setStudents((prev) =>
        prev.map((s) => (s.id === id ? { ...s, is_active: false } : s))
      );
    } catch {
      setErrorMessage('Failed to deactivate student.');
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Student Management</Text>

      {/* Add student card */}
      <View style={styles.formCard}>
        <Text style={styles.formTitle}>Add New Student</Text>

        {errorMessage && (
          <Text style={styles.errorText}>{errorMessage}</Text>
        )}

        <TextInput
          placeholder="Student ID (e.g. S045)"
          placeholderTextColor={THEME.colors.textMuted}
          value={studentId}
          onChangeText={setStudentId}
          style={styles.input}
        />
        <TextInput
          placeholder="Full Name"
          placeholderTextColor={THEME.colors.textMuted}
          value={name}
          onChangeText={setName}
          style={styles.input}
        />

        <TouchableOpacity
          onPress={handleAddStudent}
          style={styles.addButton}
          accessibilityRole="button"
          accessibilityLabel="Add Student"
        >
          <Text style={styles.addButtonText}>Add Student</Text>
        </TouchableOpacity>
      </View>

      {/* Student List */}
      {loading ? (
        <ActivityIndicator color={THEME.colors.accentPrimary} />
      ) : (
        <FlatList
          data={students}
          keyExtractor={(item) => item.id.toString()}
          renderItem={({ item }) => (
            <View style={styles.studentCard}>
              <View style={styles.infoCol}>
                <Text style={styles.nameText}>{item.name}</Text>
                <Text style={styles.metaText}>
                  ID: {item.student_id} | {item.department} | Year {item.year}
                </Text>
                <Text
                  style={[
                    styles.statusText,
                    {
                      color: item.is_active
                        ? THEME.colors.accentSuccess
                        : THEME.colors.accentDanger,
                    },
                  ]}
                >
                  Status: {item.is_active ? 'Active' : 'Inactive'}
                </Text>
              </View>

              {item.is_active && (
                <TouchableOpacity
                  onPress={() => handleDeactivate(item.id)}
                  style={styles.deactivateBtn}
                  accessibilityRole="button"
                  accessibilityLabel={`Deactivate ${item.name}`}
                >
                  <Text style={styles.deactivateBtnText}>Deactivate</Text>
                </TouchableOpacity>
              )}
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
  formCard: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    borderRadius: THEME.radius.xl,
    padding: THEME.spacing.space8,
    marginBottom: THEME.spacing.space6,
  },
  formTitle: {
    fontSize: THEME.typography.sizes.sm,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
    marginBottom: THEME.spacing.space4,
  },
  errorText: {
    color: THEME.colors.accentDanger,
    fontSize: THEME.typography.sizes.xs,
    marginBottom: THEME.spacing.space3,
    fontWeight: 'bold',
  },
  input: {
    minHeight: THEME.spacing.space11, // 44dp
    borderWidth: 1,
    borderColor: THEME.colors.borderStrong,
    borderRadius: THEME.radius.lg,
    paddingHorizontal: THEME.spacing.space4,
    marginBottom: THEME.spacing.space3,
    fontSize: THEME.typography.sizes.sm,
    color: THEME.colors.textPrimary,
  },
  addButton: {
    minHeight: THEME.spacing.space11, // 44dp
    backgroundColor: THEME.colors.accentPrimary,
    borderRadius: THEME.radius.lg,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: THEME.spacing.space2,
  },
  addButtonText: {
    color: THEME.colors.bgSurface,
    fontSize: THEME.typography.sizes.sm,
    fontWeight: 'bold',
  },
  listContent: {
    paddingBottom: THEME.spacing.space10,
  },
  studentCard: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    borderRadius: THEME.radius.lg,
    padding: THEME.spacing.space6,
    marginBottom: THEME.spacing.space3,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  infoCol: {
    flex: 1,
  },
  nameText: {
    fontSize: THEME.typography.sizes.base,
    fontWeight: 'bold',
    color: THEME.colors.textPrimary,
  },
  metaText: {
    fontSize: THEME.typography.sizes.xs,
    color: THEME.colors.textSecondary,
    marginTop: THEME.spacing.space1,
  },
  statusText: {
    fontSize: THEME.typography.sizes.xs,
    fontWeight: '600',
    marginTop: THEME.spacing.space1,
  },
  deactivateBtn: {
    minHeight: THEME.spacing.space11, // 44dp
    paddingHorizontal: THEME.spacing.space4,
    justifyContent: 'center',
    alignItems: 'center',
    borderColor: THEME.colors.accentDanger,
    borderWidth: 1,
    borderRadius: THEME.radius.md,
  },
  deactivateBtnText: {
    color: THEME.colors.accentDanger,
    fontSize: THEME.typography.sizes.xs,
    fontWeight: 'bold',
  },
});
