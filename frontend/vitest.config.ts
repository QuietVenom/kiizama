import path from "node:path"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vitest/config"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    maxWorkers: 4,
    testTimeout: 20_000,
    passWithNoTests: true,
    setupFiles: ["./tests/setup/vitest.setup.ts"],
    include: [
      "tests/unit/**/*.{test,spec}.{ts,tsx}",
      "tests/unit/**/test_*.{ts,tsx}",
      "tests/component/**/*.{test,spec}.{ts,tsx}",
      "tests/component/**/test_*.{ts,tsx}",
      "tests/contract/**/*.{test,spec}.{ts,tsx}",
      "tests/contract/**/test_*.{ts,tsx}",
      "src/**/*.{test,spec}.{ts,tsx}",
    ],
    exclude: [
      "tests/e2e/**",
      "tests/legacy-node/**",
      "node_modules/**",
      "dist/**",
    ],
  },
})
