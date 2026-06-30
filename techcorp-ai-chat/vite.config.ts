import { defineConfig } from "vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";

// Si `npx create-start-app` génère un vite.config différent (nouvelles versions),
// garde le sien et ne reprends d'ici que le plugin tanstackStart().
export default defineConfig({
  server: { port: 3000 },
  plugins: [tanstackStart()],
});
