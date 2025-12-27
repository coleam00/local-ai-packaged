/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Design System: LocalAI Stack Manager - Dark Theme
        background: {
          primary: '#121827',
          secondary: '#1e293b',
          input: '#2d3748',
        },
        border: {
          subtle: '#374151',
        },
        status: {
          running: {
            bg: '#1e40af',
            text: '#dbeafe',
          },
          healthy: {
            bg: '#065f46',
            text: '#d1fae5',
          },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'card': '12px',
      },
    },
  },
  plugins: [],
}
