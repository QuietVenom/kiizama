import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { createRef } from "react"
import { describe, expect, test } from "vitest"

import FAQ from "../../../src/components/Landing/FAQ"
import { renderWithProviders } from "../helpers/render"

describe("landing FAQ", () => {
  test("faq_request_limits_answer_includes_base_plan_consumption_limits", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<FAQ sectionRef={createRef<HTMLElement>()} />, {
      language: "en",
    })

    // Act
    await user.click(
      screen.getByRole("button", {
        name: /Are there operational limits per request?/,
      }),
    )

    // Assert
    expect(
      screen.getByText(
        /The Base plan currently includes 50 profile lookups, 20 social media reports, and 5 reputation strategy requests per monthly cycle./,
      ),
    ).toBeVisible()
    expect(
      screen.getByText(
        /We will add new plans or adjust limits as demand grows./,
      ),
    ).toBeVisible()
  })
})
