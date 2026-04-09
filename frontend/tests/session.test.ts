import assert from "node:assert/strict"
import test from "node:test"
import { UsersService } from "../src/client/index.ts"
import {
  clearStoredAccessToken,
  ensureValidStoredSession,
  getStoredAccessToken,
  hasStoredAccessToken,
  setStoredAccessToken,
} from "../src/features/auth/session.ts"

class MemoryStorage {
  private store = new Map<string, string>()

  clear() {
    this.store.clear()
  }

  getItem(key: string) {
    return this.store.has(key) ? this.store.get(key)! : null
  }

  removeItem(key: string) {
    this.store.delete(key)
  }

  setItem(key: string, value: string) {
    this.store.set(key, value)
  }
}

const originalLocalStorageDescriptor = Object.getOwnPropertyDescriptor(
  globalThis,
  "localStorage",
)
const originalReadUserMe = UsersService.readUserMe

test.beforeEach(() => {
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: new MemoryStorage(),
  })
})

test.afterEach(() => {
  UsersService.readUserMe = originalReadUserMe
})

test.after(() => {
  if (originalLocalStorageDescriptor) {
    Object.defineProperty(
      globalThis,
      "localStorage",
      originalLocalStorageDescriptor,
    )
    return
  }

  delete (globalThis as { localStorage?: unknown }).localStorage
})

test("returns false when there is no stored access token", async () => {
  UsersService.readUserMe = async () => {
    throw new Error("should not be called without a token")
  }

  await assert.doesNotReject(async () => {
    assert.equal(await ensureValidStoredSession(), false)
  })
})

test("keeps the stored token when the current session is still valid", async () => {
  setStoredAccessToken("valid-token")
  UsersService.readUserMe = async () =>
    ({
      id: "user-1",
    }) as never

  assert.equal(hasStoredAccessToken(), true)
  assert.equal(await ensureValidStoredSession(), true)
  assert.equal(getStoredAccessToken(), "valid-token")
})

test("clears the stored token when the current session is expired", async () => {
  setStoredAccessToken("expired-token")
  UsersService.readUserMe = async () => {
    throw new Error("Unauthorized")
  }

  assert.equal(await ensureValidStoredSession(), false)
  assert.equal(hasStoredAccessToken(), false)
  assert.equal(getStoredAccessToken(), null)

  setStoredAccessToken("second-token")
  clearStoredAccessToken()
  assert.equal(hasStoredAccessToken(), false)
})
