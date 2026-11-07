import { readFileSync } from "node:fs"
import path from "node:path"
import { beforeEach, expect, test } from "vitest"
import {
  configureInstallationMetadata,
  isInstallationHost,
} from "@/components/Installation/metadata"

const publicDir = path.resolve(import.meta.dirname, "../../../public")
const manifest = JSON.parse(
  readFileSync(path.join(publicDir, "manifest.webmanifest"), "utf8"),
)

beforeEach(() => {
  document.head.querySelectorAll('link[rel="manifest"]').forEach((link) => {
    link.remove()
  })
})

test.each([
  "app.kiizama.com",
  "app.staging.kiizama.com",
  "localhost",
  "127.0.0.1",
  "preview.example.com",
])("application host advertises installation: %s", (hostname) => {
  expect(isInstallationHost(hostname)).toBe(true)
})
test.each([
  "www.kiizama.com",
  "kiizama.com",
  "www.staging.kiizama.com",
  "staging.kiizama.com",
])("marketing host does not advertise a separate app: %s", (hostname) => {
  expect(isInstallationHost(hostname)).toBe(false)
})
test("bootstrap metadata is shared and idempotent", () => {
  configureInstallationMetadata()
  configureInstallationMetadata()
  expect(document.head.querySelectorAll('link[rel="manifest"]')).toHaveLength(1)
  expect(document.head.querySelector('link[rel="manifest"]')).toHaveAttribute(
    "href",
    "/manifest.webmanifest",
  )
})
test("manifest launches the protected application on the same origin, not the marketing root", () => {
  expect(manifest).toMatchObject({
    id: "/",
    start_url: "/overview",
    scope: "/",
    display: "standalone",
    prefer_related_applications: false,
  })
  const origin = new URL("https://app.kiizama.com")
  expect(new URL(manifest.start_url, origin).origin).toBe(origin.origin)
})
test("declared icons exist as PNGs with their real advertised dimensions", () => {
  expect(manifest.icons).toEqual(
    expect.arrayContaining([
      expect.objectContaining({ sizes: "192x192", purpose: "any" }),
      expect.objectContaining({ sizes: "512x512", purpose: "any" }),
      expect.objectContaining({ sizes: "512x512", purpose: "maskable" }),
    ]),
  )
  for (const icon of [
    ...manifest.icons,
    { src: "/app-icons/apple-touch-icon.png", sizes: "180x180" },
  ]) {
    const png = readFileSync(path.join(publicDir, icon.src))
    expect(png.subarray(0, 8).toString("hex")).toBe("89504e470d0a1a0a")
    expect(`${png.readUInt32BE(16)}x${png.readUInt32BE(20)}`).toBe(icon.sizes)
  }
})
