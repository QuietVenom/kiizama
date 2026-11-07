import { mkdir, readFile, writeFile } from "node:fs/promises"
import path from "node:path"
import { chromium } from "@playwright/test"

// Rasterize the repository's vector brand asset; no downloaded artwork.
// Run manually: npx tsx scripts/generate-app-icons.ts (Chromium required).
const root = path.resolve(import.meta.dirname, "..")
const svg = await readFile(
  path.join(root, "public/assets/images/symbol.svg"),
  "utf8",
)
const output = path.join(root, "public/app-icons")
await mkdir(output, { recursive: true })
const browser = await chromium.launch()
try {
  const page = await browser.newPage()
  for (const [name, size, scale] of [
    ["icon-192.png", 192, 1],
    ["icon-512.png", 512, 1],
    ["icon-maskable-512.png", 512, 0.64],
    ["apple-touch-icon.png", 180, 1],
  ] as const) {
    const data = await page.evaluate(
      async ({ svg, size, scale }) => {
        const image = new Image()
        image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
        await image.decode()
        const canvas = document.createElement("canvas")
        canvas.width = canvas.height = size
        const ctx = canvas.getContext("2d")!
        ctx.fillStyle = "#fffdf8"
        ctx.fillRect(0, 0, size, size)
        const inset = (size - size * scale) / 2
        ctx.drawImage(image, inset, inset, size * scale, size * scale)
        return canvas.toDataURL("image/png").split(",")[1]
      },
      { svg, size, scale },
    )
    await writeFile(path.join(output, name), Buffer.from(data, "base64"))
    console.log(`Generated ${name} (${size}x${size})`)
  }
} finally {
  await browser.close()
}
