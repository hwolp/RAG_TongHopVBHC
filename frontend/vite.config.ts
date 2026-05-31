import path from "path"
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: true, // Cho phép lắng nghe trên tất cả các địa chỉ IP (0.0.0.0)
    port: 5173, // Bạn có thể đổi cổng nếu muốn
  },
})
