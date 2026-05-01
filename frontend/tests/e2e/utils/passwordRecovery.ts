import type { APIRequestContext } from "@playwright/test"
import { firstSuperuser, firstSuperuserPassword } from "../config"

const apiBaseUrl = process.env.VITE_API_URL

if (typeof apiBaseUrl !== "string" || apiBaseUrl.length === 0) {
  throw new Error("Environment variable VITE_API_URL is undefined")
}

const resetPasswordHrefPattern =
  /href=["']([^"']*\/reset-password\?token=[^"']+)["']/i

export const normalizeAppUrl = (rawUrl: string, appOrigin: string) => {
  const targetUrl = new URL(rawUrl)
  const currentAppUrl = new URL(appOrigin)

  targetUrl.protocol = currentAppUrl.protocol
  targetUrl.host = currentAppUrl.host

  return targetUrl.toString()
}

async function getSuperuserAccessToken(request: APIRequestContext) {
  const response = await request.post(
    `${apiBaseUrl}/api/v1/login/access-token`,
    {
      form: {
        username: firstSuperuser,
        password: firstSuperuserPassword,
      },
    },
  )

  if (!response.ok()) {
    throw new Error(
      `Unable to authenticate superuser for password recovery tests (${response.status()})`,
    )
  }

  const body = await response.json()

  if (typeof body.access_token !== "string" || body.access_token.length === 0) {
    throw new Error(
      "Password recovery test login did not return an access token",
    )
  }

  return body.access_token
}

export async function getPasswordRecoveryLink({
  request,
  email,
  appOrigin,
}: {
  request: APIRequestContext
  email: string
  appOrigin: string
}) {
  const accessToken = await getSuperuserAccessToken(request)
  const response = await request.post(
    `${apiBaseUrl}/api/v1/password-recovery-html-content/${encodeURIComponent(email)}`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  )

  if (!response.ok()) {
    throw new Error(
      `Unable to fetch password recovery HTML content (${response.status()})`,
    )
  }

  const htmlContent = await response.text()
  const match = htmlContent.match(resetPasswordHrefPattern)

  if (!match) {
    throw new Error(
      "Password recovery HTML did not include a reset-password link",
    )
  }

  return normalizeAppUrl(match[1], appOrigin)
}
