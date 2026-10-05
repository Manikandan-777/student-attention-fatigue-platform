import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  Modal,
  Switch,
  ScrollView,
} from 'react-native';
import {
  ArrowLeft,
  Plus,
  Search,
  MoreVertical,
  Trash2,
  Eye,
  EyeOff,
  ChevronDown,
  Check,
} from 'lucide-react-native';
import { THEME } from '../theme';
import { ApiService } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import { Teacher, Classroom } from '../types';

type ScreenMode = 'list' | 'add' | 'edit';

export const ManageTeachersScreen: React.FC = () => {
  const [mode, setMode] = useState<ScreenMode>('list');
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Selected teacher for edit/delete
  const [selectedTeacher, setSelectedTeacher] = useState<Teacher | null>(null);

  // Add / Edit Form State
  const [formDisplayName, setFormDisplayName] = useState('');
  const [formUsername, setFormUsername] = useState('');
  const [formPassword, setFormPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [formClassroomId, setFormClassroomId] = useState<number | null>(null);
  const [formActive, setFormActive] = useState(true);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Dropdown & Action Modals
  const [classroomPickerVisible, setClassroomPickerVisible] = useState(false);
  const [actionMenuTeacher, setActionMenuTeacher] = useState<Teacher | null>(null);
  const [deleteModalVisible, setDeleteModalVisible] = useState(false);
  const [teacherToDelete, setTeacherToDelete] = useState<Teacher | null>(null);

  const formValuesRef = useRef({ name: '', username: '', password: '' });

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      const [tList, cList] = await Promise.all([
        ApiService.getTeachers(),
        ApiService.getClassrooms().catch(() => []),
      ]);
      setTeachers(tList);
      setClassrooms(cList);
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInitialData();
  }, []);

  const openAddMode = () => {
    formValuesRef.current = { name: '', username: '', password: '' };
    setFormDisplayName('');
    setFormUsername('');
    setFormPassword('');
    setShowPassword(false);
    setFormClassroomId(classrooms.length > 0 ? classrooms[0].id : null);
    setFormActive(true);
    setFormError(null);
    setMode('add');
  };

  const openEditMode = (teacher: Teacher) => {
    setSelectedTeacher(teacher);
    formValuesRef.current = { name: teacher.display_name, username: teacher.username, password: '' };
    setFormDisplayName(teacher.display_name);
    setFormUsername(teacher.username);
    setFormPassword('');
    setFormClassroomId(teacher.classroom_id || (classrooms.length > 0 ? classrooms[0].id : null));
    setFormActive(teacher.active);
    setFormError(null);
    setActionMenuTeacher(null);
    setMode('edit');
  };

  const handleCreateTeacher = async () => {
    const displayName = (formDisplayName || formValuesRef.current.name).trim();
    const username = (formUsername || formValuesRef.current.username).trim();
    const password = (formPassword || formValuesRef.current.password).trim();

    if (!displayName || !username || !password) {
      setFormError('Please enter full name, username, and password.');
      return;
    }

    setSubmitting(true);
    setFormError(null);

    try {
      const created = await ApiService.createTeacher({
        display_name: displayName,
        username: username,
        password: password,
        classroom_id: formClassroomId || undefined,
        active: formActive,
      });

      setTeachers((prev) => [...prev, created]);
      setMode('list');
    } catch (err: any) {
      const msg = err?.response?.data?.detail?.message || err?.response?.data?.detail || 'Failed to create teacher.';
      setFormError(typeof msg === 'string' ? msg : 'Failed to create teacher.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateTeacher = async () => {
    if (!selectedTeacher) return;
    if (!formDisplayName.trim()) {
      setFormError('Full name is required.');
      return;
    }

    setSubmitting(true);
    setFormError(null);

    try {
      const updated = await ApiService.updateTeacher(selectedTeacher.id, {
        display_name: formDisplayName.trim(),
        active: formActive,
        classroom_id: formClassroomId || undefined,
      });

      setTeachers((prev) => prev.map((t) => (t.id === selectedTeacher.id ? updated : t)));
      setMode('list');
    } catch (err: any) {
      const msg = err?.response?.data?.detail?.message || err?.response?.data?.detail || 'Failed to update teacher.';
      setFormError(typeof msg === 'string' ? msg : 'Failed to update teacher.');
    } finally {
      setSubmitting(false);
    }
  };

  const confirmDeleteTeacher = (teacher: Teacher) => {
    setActionMenuTeacher(null);
    setTeacherToDelete(teacher);
    setDeleteModalVisible(true);
  };

  const handleDeleteTeacher = async () => {
    if (!teacherToDelete) return;
    try {
      await ApiService.deleteTeacher(teacherToDelete.id);
      // Remove teacher from UI list immediately
      setTeachers((prev) => prev.filter((t) => t.id !== teacherToDelete.id));
    } catch (err: any) {
      // Handle error
    } finally {
      setDeleteModalVisible(false);
      setTeacherToDelete(null);
    }
  };

  // Filter teachers by search input
  const filteredTeachers = teachers.filter((t) => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      t.display_name.toLowerCase().includes(q) ||
      t.username.toLowerCase().includes(q) ||
      (t.classroom_name && t.classroom_name.toLowerCase().includes(q))
    );
  });

  const selectedClassroom = classrooms.find((c) => c.id === formClassroomId);
  const classroomLabel = selectedClassroom
    ? `${selectedClassroom.class_name}`
    : 'Select classroom';

  // -------------------------------------------------------------
  // Screen 7: Add Teacher Form
  // -------------------------------------------------------------
  if (mode === 'add') {
    return (
      <ScrollView style={styles.container} contentContainerStyle={styles.formContainer}>
        {/* Header */}
        <View style={styles.subHeader}>
          <TouchableOpacity onPress={() => setMode('list')} style={styles.backButton}>
            <ArrowLeft size={22} color="#0F172A" />
          </TouchableOpacity>
          <Text style={styles.subHeaderTitle}>Add Teacher</Text>
          <View style={{ width: 22 }} />
        </View>

        {formError ? <Text style={styles.formErrorText}>{formError}</Text> : null}

        {/* Full Name */}
        <Text style={styles.fieldLabel}>Full Name</Text>
        <TextInput
          value={formDisplayName}
          onChangeText={(text) => {
            formValuesRef.current.name = text;
            setFormDisplayName(text);
          }}
          placeholder="Enter full name"
          placeholderTextColor="#94A3B8"
          style={styles.textInput}
        />

        {/* Username */}
        <Text style={styles.fieldLabel}>Username</Text>
        <TextInput
          value={formUsername}
          onChangeText={(text) => {
            formValuesRef.current.username = text;
            setFormUsername(text);
          }}
          placeholder="Enter username"
          autoCapitalize="none"
          placeholderTextColor="#94A3B8"
          style={styles.textInput}
        />

        {/* Password */}
        <Text style={styles.fieldLabel}>Password</Text>
        <View style={styles.passwordInputContainer}>
          <TextInput
            value={formPassword}
            onChangeText={(text) => {
              formValuesRef.current.password = text;
              setFormPassword(text);
            }}
            placeholder="Enter password"
            secureTextEntry={!showPassword}
            placeholderTextColor="#94A3B8"
            style={styles.passwordInput}
          />
          <TouchableOpacity
            onPress={() => setShowPassword(!showPassword)}
            style={styles.eyeBtn}
          >
            {showPassword ? <EyeOff size={18} color="#94A3B8" /> : <Eye size={18} color="#94A3B8" />}
          </TouchableOpacity>
        </View>

        {/* Assign Classroom Dropdown */}
        <Text style={styles.fieldLabel}>Assign Classroom</Text>
        <TouchableOpacity
          style={styles.dropdownBtn}
          onPress={() => setClassroomPickerVisible(true)}
        >
          <Text style={styles.dropdownBtnText}>{classroomLabel}</Text>
          <ChevronDown size={18} color="#64748B" />
        </TouchableOpacity>

        {/* Enable Account Switch */}
        <View style={styles.switchRow}>
          <Text style={styles.switchLabel}>Enable Account</Text>
          <Switch
            value={formActive}
            onValueChange={setFormActive}
            trackColor={{ false: '#E2E8F0', true: '#4F46E5' }}
            thumbColor="#FFFFFF"
          />
        </View>

        {/* Create Teacher Button */}
        <TouchableOpacity
          testID="btn-create-teacher"
          accessibilityRole="button"
          accessibilityLabel="Create Teacher"
          style={styles.submitBtn}
          onPress={handleCreateTeacher}
          disabled={submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.submitBtnText}>Create Teacher</Text>
          )}
        </TouchableOpacity>

        {/* Classroom Selection Modal */}
        <Modal visible={classroomPickerVisible} transparent animationType="fade">
          <TouchableOpacity
            style={styles.modalOverlay}
            activeOpacity={1}
            onPress={() => setClassroomPickerVisible(false)}
          >
            <View style={styles.modalBox}>
              <Text style={styles.modalTitle}>Select Classroom</Text>
              {classrooms.map((c) => (
                <TouchableOpacity
                  key={c.id}
                  style={[styles.pickerItem, formClassroomId === c.id && styles.pickerItemSelected]}
                  onPress={() => {
                    setFormClassroomId(c.id);
                    setClassroomPickerVisible(false);
                  }}
                >
                  <Text style={[styles.pickerItemText, formClassroomId === c.id && styles.pickerItemTextSelected]}>
                    {c.class_name} ({c.room_name})
                  </Text>
                  {formClassroomId === c.id && <Check size={18} color="#4F46E5" />}
                </TouchableOpacity>
              ))}
            </View>
          </TouchableOpacity>
        </Modal>
      </ScrollView>
    );
  }

  // -------------------------------------------------------------
  // Screen 8: Edit Teacher Form
  // -------------------------------------------------------------
  if (mode === 'edit' && selectedTeacher) {
    return (
      <ScrollView style={styles.container} contentContainerStyle={styles.formContainer}>
        {/* Header */}
        <View style={styles.subHeader}>
          <TouchableOpacity onPress={() => setMode('list')} style={styles.backButton}>
            <ArrowLeft size={22} color="#0F172A" />
          </TouchableOpacity>
          <Text style={styles.subHeaderTitle}>Edit Teacher</Text>
          <View style={{ width: 22 }} />
        </View>

        {/* Avatar Profile Card */}
        <View style={styles.editProfileCard}>
          <View style={styles.editAvatar}>
            <Text style={styles.avatarText}>
              {selectedTeacher.display_name.slice(0, 2).toUpperCase()}
            </Text>
          </View>
          <Text style={styles.editTeacherName}>{selectedTeacher.display_name}</Text>
          <StatusBadge status={formActive ? 'Active' : 'Inactive'} prefixPlus={formActive} />
        </View>

        {formError ? <Text style={styles.formErrorText}>{formError}</Text> : null}

        {/* Full Name */}
        <Text style={styles.fieldLabel}>Full Name</Text>
        <TextInput
          value={formDisplayName}
          onChangeText={setFormDisplayName}
          placeholder="Full name"
          placeholderTextColor="#94A3B8"
          style={styles.textInput}
        />

        {/* Username */}
        <Text style={styles.fieldLabel}>Username</Text>
        <TextInput
          value={formUsername}
          editable={false}
          placeholder="Username"
          placeholderTextColor="#94A3B8"
          style={[styles.textInput, styles.disabledInput]}
        />

        {/* Assign Classroom Dropdown */}
        <Text style={styles.fieldLabel}>Assign Classroom</Text>
        <TouchableOpacity
          style={styles.dropdownBtn}
          onPress={() => setClassroomPickerVisible(true)}
        >
          <Text style={styles.dropdownBtnText}>{classroomLabel}</Text>
          <ChevronDown size={18} color="#64748B" />
        </TouchableOpacity>

        {/* Status Switch */}
        <View style={styles.switchRow}>
          <Text style={styles.switchLabel}>Status</Text>
          <Switch
            value={formActive}
            onValueChange={setFormActive}
            trackColor={{ false: '#E2E8F0', true: '#4F46E5' }}
            thumbColor="#FFFFFF"
          />
        </View>

        {/* Update Teacher Button */}
        <TouchableOpacity
          style={styles.submitBtn}
          onPress={handleUpdateTeacher}
          disabled={submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.submitBtnText}>Update Teacher</Text>
          )}
        </TouchableOpacity>

        {/* Classroom Selection Modal */}
        <Modal visible={classroomPickerVisible} transparent animationType="fade">
          <TouchableOpacity
            style={styles.modalOverlay}
            activeOpacity={1}
            onPress={() => setClassroomPickerVisible(false)}
          >
            <View style={styles.modalBox}>
              <Text style={styles.modalTitle}>Select Classroom</Text>
              {classrooms.map((c) => (
                <TouchableOpacity
                  key={c.id}
                  style={[styles.pickerItem, formClassroomId === c.id && styles.pickerItemSelected]}
                  onPress={() => {
                    setFormClassroomId(c.id);
                    setClassroomPickerVisible(false);
                  }}
                >
                  <Text style={[styles.pickerItemText, formClassroomId === c.id && styles.pickerItemTextSelected]}>
                    {c.class_name} ({c.room_name})
                  </Text>
                  {formClassroomId === c.id && <Check size={18} color="#4F46E5" />}
                </TouchableOpacity>
              ))}
            </View>
          </TouchableOpacity>
        </Modal>
      </ScrollView>
    );
  }

  // -------------------------------------------------------------
  // Screen 6: Teachers List Screen
  // -------------------------------------------------------------
  return (
    <View style={styles.container}>
      {/* Header with Title and + Add Button */}
      <View style={styles.listHeader}>
        <View style={styles.headerLeft}>
          <Text style={styles.headerTitle}>Teachers</Text>
        </View>
        <TouchableOpacity
          testID="btn-add-teacher"
          style={styles.addPillBtn}
          onPress={openAddMode}
          activeOpacity={0.8}
          accessibilityRole="button"
          accessibilityLabel="+ Add Teacher"
        >
          <Plus size={16} color="#FFFFFF" strokeWidth={2.6} />
          <Text style={styles.addPillText}>Add</Text>
        </TouchableOpacity>
      </View>

      {/* Search Input Bar */}
      <View style={styles.searchBar}>
        <Search size={18} color="#94A3B8" style={styles.searchIcon} />
        <TextInput
          value={searchQuery}
          onChangeText={setSearchQuery}
          placeholder="Search teachers..."
          placeholderTextColor="#94A3B8"
          style={styles.searchInput}
        />
      </View>

      {/* Teachers List */}
      {loading ? (
        <View style={styles.centerLoading}>
          <ActivityIndicator color="#4F46E5" size="large" />
        </View>
      ) : (
        <FlatList
          data={filteredTeachers}
          keyExtractor={(item) => item.id.toString()}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.listContent}
          renderItem={({ item }) => {
            const initials = item.display_name
              .split(' ')
              .map((n) => n[0])
              .join('')
              .slice(0, 2)
              .toUpperCase();

            return (
              <View style={styles.teacherRow}>
                {/* Circular Avatar */}
                <View style={styles.avatarCircle}>
                  <Text style={styles.avatarCircleText}>{initials || 'TR'}</Text>
                </View>

                {/* Name & Class info */}
                <View style={styles.teacherInfo}>
                  <Text style={styles.teacherName}>{item.display_name}</Text>
                  <Text style={styles.teacherClass}>
                    {item.classroom_name || 'AI & DS - A Section'}
                  </Text>
                </View>

                {/* Status Badge */}
                <StatusBadge status={item.active ? 'Active' : 'Inactive'} size="sm" />

                {/* 3-dots action icon */}
                <TouchableOpacity
                  style={styles.moreBtn}
                  onPress={() => setActionMenuTeacher(item)}
                  accessibilityRole="button"
                  accessibilityLabel={`Manage ${item.display_name}`}
                >
                  <MoreVertical size={18} color="#94A3B8" />
                </TouchableOpacity>
              </View>
            );
          }}
        />
      )}

      {/* Action Menu Modal (Edit / Delete) */}
      <Modal visible={!!actionMenuTeacher} transparent animationType="fade">
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setActionMenuTeacher(null)}
        >
          <View style={styles.actionMenuBox}>
            <Text style={styles.actionMenuTitle}>{actionMenuTeacher?.display_name}</Text>
            <TouchableOpacity
              style={styles.actionMenuItem}
              onPress={() => actionMenuTeacher && openEditMode(actionMenuTeacher)}
            >
              <Text style={styles.actionMenuText}>Edit Teacher</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.actionMenuItem, styles.actionMenuItemDanger]}
              onPress={() => actionMenuTeacher && confirmDeleteTeacher(actionMenuTeacher)}
            >
              <Text style={styles.actionMenuTextDanger}>Delete Teacher</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </Modal>

      {/* Screen 9: Delete Teacher Confirmation Modal */}
      <Modal visible={deleteModalVisible} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.deleteModalBox}>
            <View style={styles.trashCircle}>
              <Trash2 size={26} color="#DC2626" />
            </View>
            <Text style={styles.deleteModalTitle}>Delete Teacher?</Text>
            <Text style={styles.deleteModalSubtext}>
              Are you sure you want to delete{'\n'}
              <Text style={{ fontWeight: '700' }}>{teacherToDelete?.display_name}</Text>?{'\n'}
              This action cannot be undone.
            </Text>

            <View style={styles.deleteBtnRow}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={() => {
                  setDeleteModalVisible(false);
                  setTeacherToDelete(null);
                }}
              >
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.confirmDeleteBtn}
                onPress={handleDeleteTeacher}
              >
                <Text style={styles.confirmDeleteText}>Delete</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8FAFC',
  },
  listHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 10,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: '#0F172A',
  },
  addPillBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#4F46E5',
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 20,
  },
  addPillText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 13,
    marginLeft: 3,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    marginHorizontal: 16,
    marginBottom: 12,
    borderRadius: 12,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    minHeight: 44,
  },
  searchIcon: {
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 14,
    color: '#0F172A',
    paddingVertical: 8,
  },
  listContent: {
    paddingHorizontal: 16,
    paddingBottom: 24,
  },
  teacherRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    paddingVertical: 12,
    paddingHorizontal: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#F1F5F9',
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.03,
    shadowRadius: 2,
  },
  avatarCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#E0E7FF',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  avatarCircleText: {
    color: '#4338CA',
    fontWeight: '700',
    fontSize: 13,
  },
  teacherInfo: {
    flex: 1,
  },
  teacherName: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0F172A',
  },
  teacherClass: {
    fontSize: 11.5,
    color: '#64748B',
    marginTop: 2,
  },
  moreBtn: {
    padding: 6,
    marginLeft: 4,
  },
  centerLoading: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // Form styles (Add & Edit)
  formContainer: {
    paddingHorizontal: 20,
    paddingTop: 14,
    paddingBottom: 36,
  },
  subHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  backButton: {
    padding: 4,
  },
  subHeaderTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#0F172A',
  },
  fieldLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#334155',
    marginBottom: 6,
    marginTop: 10,
  },
  textInput: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    paddingHorizontal: 14,
    minHeight: 48,
    fontSize: 14,
    color: '#0F172A',
  },
  disabledInput: {
    backgroundColor: '#F1F5F9',
    color: '#64748B',
  },
  passwordInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    paddingHorizontal: 14,
    minHeight: 48,
  },
  passwordInput: {
    flex: 1,
    fontSize: 14,
    color: '#0F172A',
    paddingVertical: 10,
  },
  eyeBtn: {
    padding: 4,
  },
  dropdownBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    paddingHorizontal: 14,
    minHeight: 48,
  },
  dropdownBtnText: {
    fontSize: 14,
    color: '#0F172A',
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginVertical: 18,
  },
  switchLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
  },
  submitBtn: {
    backgroundColor: '#4F46E5',
    borderRadius: 14,
    minHeight: 50,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 8,
  },
  submitBtnText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },
  formErrorText: {
    color: '#DC2626',
    fontSize: 12.5,
    marginBottom: 10,
    fontWeight: '600',
  },
  editProfileCard: {
    alignItems: 'center',
    paddingVertical: 16,
    marginBottom: 10,
  },
  editAvatar: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#EEF2FF',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  avatarText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#4F46E5',
  },
  editTeacherName: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 6,
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  modalBox: {
    width: '100%',
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 18,
    maxHeight: 320,
  },
  modalTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 12,
  },
  pickerItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  pickerItemSelected: {
    backgroundColor: '#EEF2FF',
  },
  pickerItemText: {
    fontSize: 13.5,
    color: '#334155',
  },
  pickerItemTextSelected: {
    color: '#4F46E5',
    fontWeight: '700',
  },
  // Action Menu
  actionMenuBox: {
    width: '85%',
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 18,
  },
  actionMenuTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 14,
  },
  actionMenuItem: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  actionMenuItemDanger: {
    borderBottomWidth: 0,
  },
  actionMenuText: {
    fontSize: 14,
    color: '#334155',
    fontWeight: '500',
  },
  actionMenuTextDanger: {
    fontSize: 14,
    color: '#DC2626',
    fontWeight: '600',
  },
  // Delete Modal
  deleteModalBox: {
    width: '88%',
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 22,
    alignItems: 'center',
  },
  trashCircle: {
    width: 54,
    height: 54,
    borderRadius: 27,
    backgroundColor: '#FEE2E2',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 14,
  },
  deleteModalTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 6,
  },
  deleteModalSubtext: {
    fontSize: 13,
    color: '#64748B',
    textAlign: 'center',
    lineHeight: 18,
    marginBottom: 20,
  },
  deleteBtnRow: {
    flexDirection: 'row',
    width: '100%',
    justifyContent: 'space-between',
  },
  cancelBtn: {
    flex: 1,
    backgroundColor: '#F1F5F9',
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
    marginRight: 8,
  },
  cancelBtnText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#475569',
  },
  confirmDeleteBtn: {
    flex: 1,
    backgroundColor: '#EF4444',
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
    marginLeft: 8,
  },
  confirmDeleteText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFFFFF',
  },
});
