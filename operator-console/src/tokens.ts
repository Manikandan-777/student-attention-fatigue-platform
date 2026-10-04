// UI-2 Design Tokens — Single Source of Truth
// Generated from docs/ui.md

export const TOKENS = {
  colors: {
    // Semantic Backgrounds
    'bg-surface': '#FFFFFF',
    'bg-info': '#ECF3FF',
    'bg-success': '#ECFDF3',

    // Semantic Text
    'text-primary': '#101828',
    'text-body': '#344054',
    'text-secondary': '#667085',
    'text-muted': '#98A2B3',

    // Semantic Accents
    'accent-primary': '#465FFF',
    'accent-danger': '#D92D20',
    'accent-success': '#039855',

    // Semantic Borders
    'border-strong': '#D0D5DD',
    'border-subtle': '#E4E7EC',
  },
  typography: {
    fontFamily: 'Outfit, -apple-system, system-ui, sans-serif',
    weights: {
      regular: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
    },
    sizes: {
      xs: '11px',
      sm: '13px',
      base: '16px',
      lg: '18px',
      xl: '30px',
    },
    lineHeights: {
      xs: '16px',
      sm: '18px',
      base: '24px',
      lg: '28px',
      xl: '38px',
    },
  },
  spacing: {
    '1': '2px',
    '2': '4px',
    '3': '5px',
    '4': '6px',
    '5': '7px',
    '6': '8px',
    '7': '10px',
    '8': '12px',
    '9': '16px',
    '10': '24px',
    '11': '44px',
    '12': '48px',
    '13': '56px',
  },
  radius: {
    md: '4px',
    lg: '6px',
    xl: '8px',
    full: '16px',
    pill: '9999px',
  },
  shadow: {
    sm: '0 1px 2px 0 rgba(16,24,40,0.05)',
  },
} as const;

export const STATUS_MAPPING = {
  Attentive: {
    textColor: TOKENS.colors['accent-success'],
    bgColor: TOKENS.colors['bg-success'],
    borderColor: TOKENS.colors['accent-success'],
    icon: 'check-circle',
    text: 'Attentive',
  },
  Distracted: {
    textColor: TOKENS.colors['accent-primary'],
    bgColor: TOKENS.colors['bg-info'],
    borderColor: TOKENS.colors['accent-primary'],
    icon: 'eye-off',
    text: 'Distracted',
  },
  Fatigued: {
    textColor: TOKENS.colors['accent-danger'],
    bgColor: TOKENS.colors['bg-surface'],
    borderColor: TOKENS.colors['accent-danger'],
    icon: 'alert-triangle',
    text: 'Fatigued',
  },
  Unknown: {
    textColor: TOKENS.colors['text-secondary'],
    bgColor: TOKENS.colors['bg-surface'],
    borderColor: TOKENS.colors['border-subtle'],
    icon: 'help-circle',
    text: 'Unknown',
  },
  Normal: {
    textColor: TOKENS.colors['accent-success'],
    bgColor: TOKENS.colors['bg-success'],
    borderColor: TOKENS.colors['accent-success'],
    icon: 'check-circle',
    text: 'Normal',
  },
  Online: {
    textColor: TOKENS.colors['accent-success'],
    bgColor: TOKENS.colors['bg-success'],
    borderColor: TOKENS.colors['accent-success'],
    icon: 'dot',
    text: 'Online',
  },
  Offline: {
    textColor: TOKENS.colors['accent-danger'],
    bgColor: TOKENS.colors['bg-surface'],
    borderColor: TOKENS.colors['accent-danger'],
    icon: 'dot',
    text: 'Offline',
  },
  Degraded: {
    textColor: TOKENS.colors['accent-danger'],
    bgColor: TOKENS.colors['bg-surface'],
    borderColor: TOKENS.colors['accent-danger'],
    icon: 'alert-triangle',
    text: 'Degraded',
  },
} as const;
