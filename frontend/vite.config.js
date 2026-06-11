import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: '.',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        dashboard: resolve(__dirname, 'dashboard.html'),
        processing: resolve(__dirname, 'processing.html'),
        chat: resolve(__dirname, 'chat.html'),
        document: resolve(__dirname, 'document.html')
      }
    }
  }
});
