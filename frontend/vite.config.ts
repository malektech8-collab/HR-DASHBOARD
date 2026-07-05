import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          // Normalize paths for cross-platform robustness (Windows vs POSIX)
          const normalizedPath = id.replace(/\\/g, '/');
          
          if (normalizedPath.includes('node_modules')) {
            if (normalizedPath.includes('recharts') || normalizedPath.includes('d3')) {
              return 'vendor-charts';
            }
            if (normalizedPath.includes('react') || normalizedPath.includes('scheduler')) {
              return 'vendor-react';
            }
            return 'vendor-core';
          }
          
          if (normalizedPath.includes('src/pages/')) {
            const match = normalizedPath.match(/src\/pages\/([^/]+)\.(tsx|ts)$/);
            if (match) {
              const pageName = match[1].toLowerCase();
              if (pageName !== 'commandcenter') {
                return `page-${pageName}`;
              }
            }
          }
        }
      }
    }
  }
})
