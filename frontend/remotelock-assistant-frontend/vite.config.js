import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL || 'http://localhost:8000'),
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: undefined,
      },
    },
  },
  // Add this for debugging process.env
  optimizeDeps: {
    exclude: ['process'],
  },
  // Log process.env.VITE_API_URL during build
  // This will appear in Vercel build logs
  setup(build) {
    console.log('Vercel Build - process.env.VITE_API_URL:', process.env.VITE_API_URL);
  },
})
