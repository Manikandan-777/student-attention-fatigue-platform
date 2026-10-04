// UI-7 Platform Mapping for Mobile (dp units, derived from UI-2 tokens)

export const THEME = {
  colors: {
    // Semantic Backgrounds
    bgSurface: '#FFFFFF',
    bgInfo: '#ECF3FF',
    bgSuccess: '#ECFDF3',
    bgApp: '#F8F9FA',

    // Semantic Text
    textPrimary: '#101828',
    textBody: '#344054',
    textSecondary: '#667085',
    textMuted: '#98A2B3',

    // Semantic Accents
    accentPrimary: '#465FFF',
    accentDanger: '#D92D20',
    accentSuccess: '#039855',

    // Semantic Borders
    borderStrong: '#D0D5DD',
    borderSubtle: '#E4E7EC',
  },
  spacing: {
    space1: 2,
    space2: 4,
    space3: 5,
    space4: 6,
    space5: 7,
    space6: 8,
    space7: 10,
    space8: 12,
    space9: 16,
    space10: 24,
    space11: 44, // Minimum touch target size (44x44 dp)
    space12: 48,
    space13: 56,
  },
  radius: {
    md: 4,
    lg: 6,
    xl: 8,
    full: 16,
    pill: 9999,
  },
  typography: {
    fontFamily: undefined, // Uses native system font fallback per UI-7
    sizes: {
      xs: 11,
      sm: 13,
      base: 16,
      lg: 18,
      xl: 30,
    },
    lineHeights: {
      xs: 16,
      sm: 18,
      base: 24,
      lg: 28,
      xl: 38,
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
    textColor: THEME.colors.accentPrimary,
    bgColor: THEME.colors.bgInfo,
    borderColor: THEME.colors.accentPrimary,
    icon: 'eye-off',
    text: 'Distracted',
  },
  Fatigued: {
    textColor: THEME.colors.accentDanger,
    bgColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.accentDanger,
    icon: 'alert-triangle',
    text: 'Fatigued',
  },
  Unknown: {
    textColor: THEME.colors.textSecondary,
    bgColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.borderSubtle,
    icon: 'help-circle',
    text: 'Unknown',
  },
  Normal: {
    textColor: THEME.colors.accentSuccess,
    bgColor: THEME.colors.bgSuccess,
    borderColor: THEME.colors.accentSuccess,
    icon: 'check-circle',
    text: 'Normal',
  },
  Online: {
    textColor: THEME.colors.accentSuccess,
    bgColor: THEME.colors.bgSuccess,
    borderColor: THEME.colors.accentSuccess,
    icon: 'dot',
    text: 'Online',
  },
  Offline: {
    textColor: THEME.colors.accentDanger,
    bgColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.accentDanger,
    icon: 'dot',
    text: 'Offline',
  },
  Degraded: {
    textColor: THEME.colors.accentDanger,
    bgColor: THEME.colors.bgSurface,
    borderColor: THEME.colors.accentDanger,
    icon: 'alert-triangle',
    text: 'Degraded',
  },
} as const;
