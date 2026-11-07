// The same frontend build serves both the marketing site and the application.
// Install only from the app origin: an installed www app would leave its scope
// when its launch URL redirects to app.kiizama.com.
export const isInstallationHost = (hostname: string) =>
  !/^(?:www\.)?(?:staging\.)?kiizama\.com$/i.test(hostname)

export function configureInstallationMetadata() {
  if (!isInstallationHost(window.location.hostname)) return
  if (document.head.querySelector('link[rel="manifest"]')) return

  const manifest = document.createElement("link")
  manifest.rel = "manifest"
  manifest.href = "/manifest.webmanifest"
  document.head.append(manifest)
}
