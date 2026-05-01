import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { useState } from "react"
import { describe, expect, test } from "vitest"

import UsernameTagsInput from "../../../src/components/CreatorsSearch/UsernameTagsInput"
import { Field } from "../../../src/components/ui/field"
import { renderWithProviders } from "../helpers/render"

const ControlledUsernameTagsInput = ({
  expiredValues,
  invalid,
  invalidValues,
  missingValues,
  onMaxExceeded,
}: {
  expiredValues?: ReadonlySet<string>
  invalid?: boolean
  invalidValues?: ReadonlySet<string>
  missingValues?: ReadonlySet<string>
  onMaxExceeded?: () => void
}) => {
  const [value, setValue] = useState<string[]>(["alpha"])

  return (
    <Field ids={{ control: "username-tags-input" }} label="Creator usernames">
      <UsernameTagsInput
        expiredValues={expiredValues}
        invalid={invalid}
        invalidValues={invalidValues}
        missingValues={missingValues}
        onMaxExceeded={onMaxExceeded}
        onValueChange={setValue}
        value={value}
      />
    </Field>
  )
}

describe("username tags input", () => {
  test("username_tags_input_values_render_with_at_prefix", () => {
    // Arrange / Act
    renderWithProviders(<ControlledUsernameTagsInput />)

    // Assert
    expect(screen.getByText("@alpha")).toBeVisible()
    expect(
      screen.getByRole("textbox", { name: "Creator usernames" }),
    ).toBeVisible()
  })

  test("username_tags_input_missing_and_expired_values_keep_remove_actions_accessible", () => {
    // Arrange / Act
    renderWithProviders(
      <ControlledUsernameTagsInput
        expiredValues={new Set(["expired"])}
        missingValues={new Set(["alpha"])}
      />,
    )

    // Assert
    expect(screen.getByRole("button", { name: "Remove alpha" })).toBeVisible()
  })

  test("username_tags_input_adding_duplicate_keeps_single_visible_tag", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<ControlledUsernameTagsInput />)

    // Act
    await user.type(
      screen.getByRole("textbox", { name: "Creator usernames" }),
      "alpha,",
    )

    // Assert
    expect(screen.getAllByText("@alpha")).toHaveLength(1)
  })

  test("username_tags_input_remove_action_updates_visible_tags", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<ControlledUsernameTagsInput />)

    // Act
    await user.click(screen.getByRole("button", { name: "Remove alpha" }))

    // Assert
    await waitFor(() => {
      expect(screen.queryByText("@alpha")).not.toBeInTheDocument()
    })
  })
})
