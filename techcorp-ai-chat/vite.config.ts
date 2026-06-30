import { defineConfig } from "vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";

// Ordre important : tanstackStart() avant viteReact().
export default defineConfig({
  server: { port: 3000 },
  plugins: [tanstackStart(), viteReact()],
});
