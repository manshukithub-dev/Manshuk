/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      colors: {
        navy: {
          950: '#050811',
          900: '#0A0F1E',
          850: '#0F1629',
          800: '#152038',
        },
      },
      boxShadow: {
        glow: '0 0 28px -6px rgba(56, 189, 248, 0.28)',
        violetGlow: '0 0 30px -6px rgba(139, 92, 246, 0.32)',
        glass:
          'inset 0 1px 0 0 rgba(255, 255, 255, 0.07), 0 14px 34px -12px rgba(0, 0, 0, 0.72)',
      },
    },
  },
  plugins: [],
};
