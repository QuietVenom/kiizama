import { describe, expect, test } from "vitest"

import { getCookieDomain } from "../../../src/lib/browser-cookies"

describe("browser cookies", () => {
  test("browser_cookies_cookie_domain_is_shared_for_kiizama_hosts", () => {
    expect(getCookieDomain("www.kiizama.com")).toBe(".kiizama.com")
    expect(getCookieDomain("app.kiizama.com")).toBe(".kiizama.com")
    expect(getCookieDomain("kiizama.com")).toBe(".kiizama.com")
  })

  test("browser_cookies_cookie_domain_prefers_staging_root_when_present", () => {
    expect(getCookieDomain("www.staging.kiizama.com")).toBe(
      ".staging.kiizama.com",
    )
    expect(getCookieDomain("app.staging.kiizama.com")).toBe(
      ".staging.kiizama.com",
    )
    expect(getCookieDomain("staging.kiizama.com")).toBe(".staging.kiizama.com")
  })

  test("browser_cookies_cookie_domain_stays_host_only_for_local_and_unknown_hosts", () => {
    expect(getCookieDomain("localhost")).toBeUndefined()
    expect(getCookieDomain("127.0.0.1")).toBeUndefined()
    expect(getCookieDomain("preview.other-domain.com")).toBeUndefined()
  })
})
