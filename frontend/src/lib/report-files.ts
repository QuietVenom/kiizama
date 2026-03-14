export const extractFilenameFromContentDisposition = (
  contentDisposition: string | null,
  fallbackFilename: string,
) => {
  if (contentDisposition) {
    const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
    if (utf8Match?.[1]) {
      return decodeURIComponent(utf8Match[1])
    }

    const basicMatch = contentDisposition.match(/filename="?([^"]+)"?/i)
    if (basicMatch?.[1]) {
      return basicMatch[1]
    }
  }

  return fallbackFilename
}

export const triggerFileDownload = (href: string, filename: string) => {
  const link = document.createElement("a")

  link.href = href
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

export const downloadBlob = (blob: Blob, filename: string) => {
  const objectUrl = window.URL.createObjectURL(blob)
  triggerFileDownload(objectUrl, filename)
  window.URL.revokeObjectURL(objectUrl)
}

export const blobToDataUrl = (blob: Blob) =>
  new Promise<string>((resolve, reject) => {
    const reader = new FileReader()

    reader.onloadend = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result)
        return
      }

      reject(new Error("Unable to store the generated file locally."))
    }
    reader.onerror = () => {
      reject(new Error("Unable to store the generated file locally."))
    }

    reader.readAsDataURL(blob)
  })
