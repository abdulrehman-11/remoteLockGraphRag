/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Official RemoteLock branding colors (Teal theme)
        remotelock: {
          50: '#e6f7f9',
          100: '#cceff3',
          200: '#99dfe7',
          300: '#66cfdb',
          400: '#33bfcf',
          500: '#0f4c5c', // Primary brand teal
          600: '#0c3d49',
          700: '#092e37',
          800: '#061f25',
          900: '#031012', // Dark teal
        },
        brand: {
          light: '#33bfcf',
          DEFAULT: '#0f4c5c',
          dark: '#031012',
        },
        success: '#2e844a',
        error: '#ea001e',
        warning: '#fe9339',
      },
      fontFamily: {
        sans: [
          'Segoe UI',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif',
          'Apple Color Emoji',
          'Segoe UI Emoji',
        ],
      },
      boxShadow: {
        'elevation-sm': '0 2px 2px rgba(0, 0, 0, 0.1)',
        'elevation-md': '0 4px 4px rgba(0, 0, 0, 0.1)',
        'focus-ring': '0 0 2px 2px #1b96ff inset',
      },
      borderRadius: {
        'remotelock': '0.5rem',
      },
      keyframes: {
        'slide-up': {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        'slide-up': 'slide-up 0.3s ease-out',
        'fade-in': 'fade-in 0.2s ease-in',
      },
    },
  },
  plugins: [],
}
