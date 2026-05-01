import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { useState } from "react"
import { describe, expect, test } from "vitest"
import { Field } from "../../../src/components/ui/field"
import { TagsInputField } from "../../../src/components/ui/tags-input-field"
import { renderWithProviders } from "../helpers/render"

const ControlledTagsInput = ({
  disabled = false,
  max,
  onMaxExceeded,
}: {
  disabled?: boolean
  max?: number
  onMaxExceeded?: () => void
}) => {
  const [value, setValue] = useState<string[]>([])

  return (
    <Field ids={{ control: "tags-input" }} label="Instagram usernames">
      <TagsInputField
        disabled={disabled}
        max={max}
        onMaxExceeded={onMaxExceeded}
        onValueChange={setValue}
        placeholder="Add username"
        renderTagLabel={(item) => `@${item}`}
        value={value}
      />
    </Field>
  )
}

describe("tags input field", () => {
  test.each([
    ["comma", "commauser,", "@commauser"],
    ["space", "spaceuser ", "@spaceuser"],
    ["enter", "enteruser{Enter}", "@enteruser"],
  ])(
    "tags_input_field_%s_commit_adds_tag_and_clears_visible_input",
    async (_delimiter, typedValue, expectedTag) => {
      // Arrange
      const user = userEvent.setup()
      renderWithProviders(<ControlledTagsInput />)
      const input = screen.getByRole("textbox", {
        name: "Instagram usernames",
      })

      // Act
      await user.type(input, typedValue)

      // Assert
      await waitFor(() => {
        expect(input).toHaveValue("")
      })
      expect(screen.getByText(expectedTag)).toBeVisible()
    },
  )

  test("tags_input_field_hidden_input_exists_and_visible_input_has_autofill_ignore_attrs", () => {
    // Arrange / Act
    const { container } = renderWithProviders(<ControlledTagsInput />)

    // Assert
    const input = screen.getByRole("textbox", { name: "Instagram usernames" })
    const hiddenInput = container.querySelector("input[hidden]")
    expect(hiddenInput).toBeTruthy()
    expect(input).toHaveAttribute("data-1p-ignore", "true")
    expect(input).toHaveAttribute("data-bwignore", "true")
    expect(input).toHaveAttribute("data-lpignore", "true")
    expect(hiddenInput).not.toHaveAttribute("data-1p-ignore")
  })

  test("tags_input_field_remove_button_deletes_existing_tag", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<ControlledTagsInput />)
    const input = screen.getByRole("textbox", {
      name: "Instagram usernames",
    })
    await user.type(input, "alpha,")
    await screen.findByText("@alpha")

    // Act
    await user.click(screen.getByRole("button", { name: "Remove alpha" }))

    // Assert
    await waitFor(() => {
      expect(screen.queryByText("@alpha")).not.toBeInTheDocument()
    })
  })

  test("tags_input_field_disabled_state_disables_textbox", () => {
    // Arrange / Act
    renderWithProviders(<ControlledTagsInput disabled />)

    // Assert
    expect(
      screen.getByRole("textbox", { name: "Instagram usernames" }),
    ).toBeDisabled()
  })

  test("tags_input_field_range_overflow_prevents_extra_tag", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(<ControlledTagsInput max={1} />)
    const input = screen.getByRole("textbox", {
      name: "Instagram usernames",
    })

    // Act
    await user.type(input, "alpha,beta,")

    // Assert
    expect(screen.getByText("@alpha")).toBeVisible()
    expect(screen.queryByText("@beta")).not.toBeInTheDocument()
  })
})
