import { expect, test } from "@playwright/test"
import { anonymousStorageState } from "./utils/storageState"

test.describe("Blog routes", () => {
  test.use({
    storageState: anonymousStorageState,
  })

  test.beforeEach(async ({ page }) => {
    await page.route(
      "**/api/v1/public/feature-flags/waiting-list",
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            key: "waiting-list",
            description: null,
            is_enabled: false,
            is_public: true,
          }),
        })
      },
    )
  })

  test("renders the blog index from markdown content", async ({ page }) => {
    await page.goto("/blog")

    await expect(page).toHaveTitle(
      "Kiizama Journal | Reputation intelligence insights",
    )
    await expect(
      page.getByRole("heading", {
        name: "De datos a decisiones que realmente importan.",
      }),
    ).toBeVisible()
    await expect(
      page.getByText(
        "Inside Kiizama: The operating system behind reputation intelligence",
      ),
    ).toHaveCount(0)
    await expect(page.getByText("Draft editorial placeholder")).toHaveCount(0)
  })

  test("navigates from the blog index to a post detail page", async ({
    page,
  }) => {
    await page.goto("/blog")

    await page
      .getByTestId(
        "blog-card-kiizama-inteligencia-creators-marcas-equipos-comunicacion",
      )
      .getByRole("button", { name: "Read More" })
      .click()

    await expect(page).toHaveURL(
      /\/blog\/kiizama-inteligencia-creators-marcas-equipos-comunicacion$/,
    )
    await expect(page).toHaveTitle(
      "Kiizama: de datos a decisiones para creators, marcas y comunicación",
    )
    await expect(page.locator('head meta[name="description"]')).toHaveAttribute(
      "content",
      "Conoce Kiizama, una plataforma de inteligencia que transforma datos de redes sociales en análisis, reportes y estrategias accionables para tomar mejores decisiones.",
    )
    await expect(page.locator('head link[rel="canonical"]')).toHaveAttribute(
      "href",
      "https://kiizama.com/blog/kiizama-inteligencia-creators-marcas-equipos-comunicacion",
    )
    await expect(
      page.getByTestId("blog-post-content").getByRole("heading", {
        name: "De datos a decisiones que realmente importan",
      }),
    ).toBeVisible()
    await expect(page.getByTestId("blog-post-content")).toContainText(
      "Kiizama es una plataforma de inteligencia para creators, marcas y equipos de comunicación",
    )
  })

  test("shows the global not found view for an unknown blog slug", async ({
    page,
  }) => {
    await page.goto("/blog/does-not-exist")

    await expect(page.getByTestId("not-found")).toBeVisible()
  })
})
