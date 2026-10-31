import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiProxy = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
    timeout: 30000,
    proxyTimeout: 30000,
    configure: (proxy: any) => {
      proxy.on('error', (_err: unknown, _req: unknown, res: any) => {
        if (res && typeof res.writeHead === 'function' && !res.headersSent) {
          res.writeHead(503, { 'Content-Type': 'application/json; charset=utf-8' });
          res.end(
            JSON.stringify({
              status: 'offline',
              detail:
                'Backend API серверімен (127.0.0.1:8000) уақытша байланыс жоқ. Frontend дербес жұмыс істеп тұр.',
            })
          );
        }
      });
    },
  },
};

const allowedHosts = ['.trycloudflare.com', '.loca.lt', 'localhost', '127.0.0.1'];

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    allowedHosts,
    proxy: apiProxy,
  },
  preview: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    allowedHosts,
    proxy: apiProxy,
  },
});
