import { screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"

import BlogPostContent from "../../../src/components/Blog/BlogPostContent"
import { renderWithProviders } from "../helpers/render"

describe("blog post content", () => {
  test("blog_post_content_sanitized_html_renders_expected_elements", () => {
    // Arrange
    const html = `
      <h2>Section title</h2>
      <p>Safe paragraph with <a href="https://kiizama.test">link</a>.</p>
      <ul><li>First item</li><li>Second item</li></ul>
      <pre><code>const value = true</code></pre>
    `

    // Act
    renderWithProviders(<BlogPostContent html={html} />)

    // Assert
    expect(screen.getByRole("heading", { name: "Section title" })).toBeVisible()
    expect(screen.getByRole("link", { name: "link" })).toHaveAttribute(
      "href",
      "https://kiizama.test",
    )
    expect(screen.getByText("First item")).toBeVisible()
    expect(screen.getByText("Second item")).toBeVisible()
    expect(screen.getByText("const value = true")).toBeVisible()
  })

  test("blog_post_content_empty_html_renders_empty_content_container", () => {
    // Arrange / Act
    renderWithProviders(<BlogPostContent html="" />)

    // Assert
    expect(screen.getByTestId("blog-post-content")).toBeEmptyDOMElement()
  })
})
