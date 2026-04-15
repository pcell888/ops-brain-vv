import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

/** 反代子路径时必设，如 /diagnose-admin/（须含首尾 /） */
const base =
  (process.env.VITE_BASE_PATH && process.env.VITE_BASE_PATH.trim()) || '/';
const normalizedBase =
  base === '/' ? '/' : `/${base.replace(/^\/+|\/+$/g, '')}/`;

export default defineConfig({
  base: normalizedBase,
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: process.env.BACKEND_URL || 'http://localhost:8100',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
});

