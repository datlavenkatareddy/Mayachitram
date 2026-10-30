import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // @ts-expect-error vitest config field supported at test runtime
  test: { environment: "jsdom", setupFiles: "./src/test-setup.ts" },
});
