import { beforeEach, describe, expect, test, vi } from "vitest"

import {
  blobToDataUrl,
  downloadBlob,
  extractFilenameFromContentDisposition,
} from "../../../src/lib/report-files"

describe("report files", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  test("report_files_extract_filename_supports_basic_and_utf8_headers", () => {
    // Arrange / Act / Assert
    expect(
      extractFilenameFromContentDisposition(
        'attachment; filename="report.pdf"',
        "fallback.pdf",
      ),
    ).toBe("report.pdf")
    expect(
      extractFilenameFromContentDisposition(
        "attachment; filename*=UTF-8''reporte%20final.pdf",
        "fallback.pdf",
      ),
    ).toBe("reporte final.pdf")
  })

  test("report_files_extract_filename_uses_fallback_when_header_missing_or_invalid", () => {
    // Arrange / Act / Assert
    expect(extractFilenameFromContentDisposition(null, "fallback.pdf")).toBe(
      "fallback.pdf",
    )
    expect(
      extractFilenameFromContentDisposition("attachment", "fallback.pdf"),
    ).toBe("fallback.pdf")
  })

  test("report_files_download_blob_creates_clicks_and_revokes_object_url", () => {
    // Arrange
    const appendChild = vi.spyOn(document.body, "appendChild")
    const removeChild = vi.spyOn(document.body, "removeChild")
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined)
    const createObjectURL = vi
      .spyOn(window.URL, "createObjectURL")
      .mockReturnValue("blob:report")
    const revokeObjectURL = vi
      .spyOn(window.URL, "revokeObjectURL")
      .mockImplementation(() => undefined)

    // Act
    downloadBlob(new Blob(["pdf"], { type: "application/pdf" }), "report.pdf")

    // Assert
    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob))
    expect(appendChild).toHaveBeenCalledWith(expect.any(HTMLAnchorElement))
    expect(click).toHaveBeenCalled()
    expect(removeChild).toHaveBeenCalledWith(expect.any(HTMLAnchorElement))
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:report")
  })

  test("report_files_download_blob_propagates_create_object_url_errors", () => {
    // Arrange
    vi.spyOn(window.URL, "createObjectURL").mockImplementation(() => {
      throw new Error("URL unavailable")
    })

    // Act / Assert
    expect(() => downloadBlob(new Blob(["pdf"]), "report.pdf")).toThrow(
      "URL unavailable",
    )
  })

  test("report_files_blob_to_data_url_resolves_data_url", async () => {
    // Arrange / Act
    const dataUrl = await blobToDataUrl(
      new Blob(["hello"], { type: "text/plain" }),
    )

    // Assert
    expect(dataUrl).toMatch(/^data:text\/plain;base64,/)
  })
})
