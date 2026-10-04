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
import { Teacher } from '../types';

export const ManageTeachersScreen: React.FC = () => {
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [department, setDepartment] = useState('Computer Science');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchTeachers = async () => {
    setLoading(true);
    try {
      const data = await ApiService.getTeachers();
      setTeachers(data);
    } catch {
      // offline fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeachers();
  }, []);

  const handleAddTeacher = async () => {
    if (!name.trim() || !email.trim()) {
      setErrorMessage('Name and Email are required.');
      return;
    }

    setErrorMessage(null);
    try {
      const newT = await ApiService.createTeacher({
        name: name.trim(),
        email: email.trim(),
        department: department.trim(),
      });
      setTeachers((prev) => [...prev, newT]);
      setName('');
      setEmail('');
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setErrorMessage(error.response?.data?.detail ?? 'Failed to create teacher.');
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Teacher Management</Text>

      <View style={styles.formCard}>
        <Text style={styles.formTitle}>Create Teacher Account</Text>

        {errorMessage && (
          <Text style={styles.errorText}>{errorMessage}</Text>
        )}

        <TextInput
          placeholder="Full Name"
          placeholderTextColor={THEME.colors.textMuted}
          value={name}
          onChangeText={setName}
          style={styles.input}
        />
        <TextInput
          placeholder="Email Address"
          placeholderTextColor={THEME.colors.textMuted}
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
          style={styles.input}
        />

        <TouchableOpacity
          onPress={handleAddTeacher}
          style={styles.addButton}
          accessibilityRole="button"
          accessibilityLabel="Add Teacher"
        >
          <Text style={styles.addButtonText}>Add Teacher</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator color={THEME.colors.accentPrimary} />
      ) : (
        <FlatList
          data={teachers}
          keyExtractor={(item) => item.id.toString()}
          renderItem={({ item }) => (
            <View style={styles.teacherCard}>
              <View>
                <Text style={styles.nameText}>{item.name}</Text>
                <Text style={styles.metaText}>{item.email} | {item.department}</Text>
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
                  Status: {item.is_active ? 'Active' : 'Disabled'}
                </Text>
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
  teacherCard: {
    backgroundColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    borderWidth: 1,
    borderRadius: THEME.radius.lg,
    padding: THEME.spacing.space6,
    marginBottom: THEME.spacing.space3,
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
});
