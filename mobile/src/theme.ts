// UI Theme matching Exact Mobile Application Design

export const THEME = {
  colors: {
    // Brand & Primary
    primary: '#4F46E5',
    primaryDark: '#4338CA',
    primaryLight: '#EEF2FF',
    accentPrimary: '#4F46E5',

    // Backgrounds
    background: '#F8FAFC',
    bgSurface: '#FFFFFF',
    bgCard: '#FFFFFF',
    bgApp: '#F8FAFC',

    // Text
    textPrimary: '#0F172A',
    textSecondary: '#475569',
    textMuted: '#94A3B8',
    textLight: '#FFFFFF',

    // Borders
    border: '#E2E8F0',
    borderSubtle: '#F1F5F9',
    borderStrong: '#CBD5E1',

    // Status / Metric Accents & Backgrounds
    students: {
      text: '#0284C7',
      bg: '#E0F2FE',
      icon: '#0284C7',
    },
    attentive: {
      text: '#16A34A',
      bg: '#DCFCE7',
      icon: '#16A34A',
    },
    distracted: {
      text: '#D97706',
      bg: '#FEF3C7',
      icon: '#D97706',
    },
    fatigued: {
      text: '#DC2626',
      bg: '#FEE2E2',
      icon: '#DC2626',
    },
    alerts: {
      text: '#7C3AED',
      bg: '#F3E8FF',
      icon: '#7C3AED',
    },

    // Semantic Accents
    accentSuccess: '#16A34A',
    bgSuccess: '#DCFCE7',
    accentWarning: '#D97706',
    bgWarning: '#FEF3C7',
    accentDanger: '#DC2626',
    bgDanger: '#FEE2E2',
    bgInfo: '#E0F2FE',
  },
  spacing: {
    space1: 2,
    space2: 4,
    space3: 6,
    space4: 8,
    space6: 12,
    space7: 14,
    space8: 16,
    space9: 20,
    space10: 24,
    space11: 44, // Minimum touch target size (44x44 dp)
    space12: 48,
    space13: 56,
  },
  radius: {
    sm: 6,
    md: 8,
    lg: 12,
    xl: 16,
    xxl: 20,
    full: 9999,
  },
  typography: {
    sizes: {
      xs: 11,
      sm: 13,
      base: 15,
      lg: 18,
      xl: 22,
      xxl: 26,
    },
  },
} as const;

export const STATUS_MAPPING = {
  Attentive: {
    textColor: THEME.colors.accentSuccess,
    bgColor: THEME.colors.bgSuccess,
    borderColor: THEME.colors.accentSuccess,
    icon: 'check-circle',
    text: 'Attentive',
  },
  Distracted: {
    textColor: THEME.colors.accentWarning,
    bgColor: THEME.colors.bgWarning,
    borderColor: THEME.colors.accentWarning,
    icon: 'eye-off',
    text: 'Distracted',
  },
  Fatigued: {
    textColor: THEME.colors.accentDanger,
    bgColor: THEME.colors.bgDanger,
    borderColor: THEME.colors.accentDanger,
    icon: 'alert-triangle',
    text: 'Fatigued',
  },
  Unknown: {
    textColor: THEME.colors.textSecondary,
    bgColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.border,
    icon: 'help-circle',
    text: 'Unknown',
  },
  Active: {
    textColor: '#15803D',
    bgColor: '#DCFCE7',
    text: 'Active',
  },
  Inactive: {
    textColor: '#64748B',
    bgColor: '#F1F5F9',
    text: 'Inactive',
  },
} as const;
