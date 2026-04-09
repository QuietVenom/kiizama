import { expect, type Locator, type Page, test } from "@playwright/test"

type Delimiter = "comma" | "enter" | "space"

const getVisibleTagsInput = (page: Page, label: string) =>
  page.getByRole("textbox", { name: label }).first()

const getTagsInputRoot = (page: Page, label: string) => {
  const visibleInput = getVisibleTagsInput(page, label)
  return page
    .locator('[data-scope="tags-input"][data-part="root"]')
    .filter({ has: visibleInput })
    .first()
}

const getHiddenTagsInput = (page: Page, label: string) =>
  getTagsInputRoot(page, label).locator("input[hidden]").first()

const assertAutofillAttrs = async (
  locator: Locator,
  expectedState: "present" | "absent",
) => {
  const expectation =
    expectedState === "present" ? expect(locator) : expect(locator).not

  await expectation.toHaveAttribute("data-1p-ignore", "true")
  await expectation.toHaveAttribute("data-bwignore", "true")
  await expectation.toHaveAttribute("data-lpignore", "true")
}

const assertTagsInputDom = async (page: Page, label: string) => {
  const visibleInput = getVisibleTagsInput(page, label)
  const hiddenInput = getHiddenTagsInput(page, label)

  await expect(visibleInput).toBeVisible()

  const [visibleId, hiddenId] = await Promise.all([
    visibleInput.getAttribute("id"),
    hiddenInput.getAttribute("id"),
  ])

  expect(visibleId).toBeTruthy()
  expect(hiddenId).toBeTruthy()
  expect(visibleId).not.toBe(hiddenId)

  await assertAutofillAttrs(visibleInput, "present")
  await assertAutofillAttrs(hiddenInput, "absent")
}

const addTagAndExpectClear = async (
  page: Page,
  label: string,
  username: string,
  delimiter: Delimiter,
) => {
  const input = getVisibleTagsInput(page, label)
  const root = getTagsInputRoot(page, label)

  await expect(input).toBeVisible()

  if (delimiter === "enter") {
    await input.pressSequentially(username)
    await input.press("Enter")
  } else {
    const suffix = delimiter === "comma" ? "," : " "
    await input.pressSequentially(`${username}${suffix}`)
  }

  await expect(root.getByText(`@${username}`, { exact: true })).toBeVisible()
  await expect(input).toHaveValue("")
}

test.describe("shared tags input", () => {
  test("creators search clears the visible input when committing with comma", async ({
    page,
  }) => {
    await page.goto("/creators-search")
    await expect(
      page.getByRole("heading", { name: "Search creators by username" }),
    ).toBeVisible()

    await assertTagsInputDom(page, "Instagram usernames")
    await addTagAndExpectClear(
      page,
      "Instagram usernames",
      "commauser",
      "comma",
    )
  })

  test("creators search clears the visible input when committing with space", async ({
    page,
  }) => {
    await page.goto("/creators-search")

    await assertTagsInputDom(page, "Instagram usernames")
    await addTagAndExpectClear(
      page,
      "Instagram usernames",
      "spaceuser",
      "space",
    )
  })

  test("creators search clears the visible input when committing with Enter", async ({
    page,
  }) => {
    await page.goto("/creators-search")

    await assertTagsInputDom(page, "Instagram usernames")
    await addTagAndExpectClear(
      page,
      "Instagram usernames",
      "enteruser",
      "enter",
    )
  })

  test("campaign reputation strategy clears the shared usernames input", async ({
    page,
  }) => {
    await page.goto("/brand-intelligence/reputation-strategy")
    await expect(
      page.getByRole("button", { name: "Reputation Campaign Strategy" }),
    ).toBeVisible()

    await assertTagsInputDom(page, "Creator usernames")
    await addTagAndExpectClear(
      page,
      "Creator usernames",
      "campaignuser",
      "comma",
    )
  })

  test("creator reputation strategy clears the controlled single-username input", async ({
    page,
  }) => {
    await page.goto("/brand-intelligence/reputation-strategy")
    await page
      .getByRole("button", { name: "Reputation Creator Strategy" })
      .click()
    await expect(
      page.getByRole("textbox", { name: "Creator username" }),
    ).toBeVisible()

    await assertTagsInputDom(page, "Creator username")
    await addTagAndExpectClear(page, "Creator username", "creatoruser", "comma")
  })
})
