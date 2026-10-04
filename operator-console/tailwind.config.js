/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bg-surface': 'var(--bg-surface, #FFFFFF)',
        'bg-info': 'var(--bg-info, #ECF3FF)',
        'bg-success': 'var(--bg-success, #ECFDF3)',
        'text-primary': 'var(--text-primary, #101828)',
        'text-body': 'var(--text-body, #344054)',
        'text-secondary': 'var(--text-secondary, #667085)',
        'text-muted': 'var(--text-muted, #98A2B3)',
        'accent-primary': 'var(--accent-primary, #465FFF)',
        'accent-danger': 'var(--accent-danger, #D92D20)',
        'accent-success': 'var(--accent-success, #039855)',
        'border-strong': 'var(--border-strong, #D0D5DD)',
        'border-subtle': 'var(--border-subtle, #E4E7EC)',
      },
      fontFamily: {
        sans: ['Outfit', '-apple-system', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        xs: ['11px', '16px'],
        sm: ['13px', '18px'],
        base: ['16px', '24px'],
        lg: ['18px', '28px'],
        xl: ['30px', '38px'],
      },
      spacing: {
        'space-1': '2px',
        'space-2': '4px',
        'space-3': '5px',
        'space-4': '6px',
        'space-5': '7px',
        'space-6': '8px',
        'space-7': '10px',
        'space-8': '12px',
        'space-9': '16px',
        'space-10': '24px',
        'space-11': '44px',
        'space-12': '48px',
        'space-13': '56px',
      },
      borderRadius: {
        'radius-md': '4px',
        'radius-lg': '6px',
        'radius-xl': '8px',
        'radius-full': '16px',
        'radius-pill': '9999px',
      },
      boxShadow: {
        'shadow-sm': '0 1px 2px 0 rgba(16,24,40,0.05)',
      },
    },
  },
  plugins: [],
}
