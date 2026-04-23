import path from "node:path"
import { tanstackRouter } from "@tanstack/router-plugin/vite"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vite"

const getNodeModulePackageName = (id: string) => {
  const match = id.match(
    /node_modules\/(?:\.pnpm\/[^/]+\/node_modules\/)?((?:@[^/]+\/[^/]+)|[^/]+)/,
  )
  return match?.[1]
}

const chunkVendorPackages = (id: string) => {
  const packageName = getNodeModulePackageName(id)

  if (!packageName) {
    return undefined
  }

  if (["react", "react-dom", "scheduler"].includes(packageName)) {
    return "react-vendor"
  }

  if (packageName.startsWith("@zag-js/")) {
    return "zag-vendor"
  }

  if (
    packageName.startsWith("@chakra-ui/") ||
    packageName.startsWith("@emotion/") ||
    packageName === "next-themes"
  ) {
    return "chakra-vendor"
  }

  if (packageName.startsWith("@tanstack/")) {
    return "tanstack-vendor"
  }

  if (packageName === "axios" || packageName === "form-data") {
    return "api-vendor"
  }

  if (packageName === "react-icons") {
    return "icons-vendor"
  }

  if (packageName === "zod") {
    return "validation-vendor"
  }

  if (packageName === "marked" || packageName === "html-react-parser") {
    return "blog-vendor"
  }

  return undefined
}

// https://vitejs.dev/config/
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: chunkVendorPackages,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  plugins: [
    tanstackRouter({
      target: "react",
      autoCodeSplitting: true,
    }),
    react(),
  ],
})
