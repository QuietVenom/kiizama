import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, test } from "vitest"

import YouTubeVideo from "../../../src/components/Blog/YouTubeVideo"
import { renderWithProviders } from "../helpers/render"

describe("YouTube video", () => {
  test("youtube_video_before_play_does_not_load_third_party_iframe", () => {
    // Arrange / Act
    renderWithProviders(
      <YouTubeVideo
        title="Tutorial: cómo buscar creators en Kiizama"
        videoId="qDZ8lIDJfoA"
      />,
      { language: "es" },
    )

    // Assert
    expect(
      screen.getByRole("button", {
        name: "Reproducir video: Tutorial: cómo buscar creators en Kiizama",
      }),
    ).toBeVisible()
    expect(screen.queryByTitle(/Reproductor del video/)).not.toBeInTheDocument()
    expect(
      screen.getByRole("link", { name: /Ver en YouTube/ }),
    ).toHaveAttribute("href", "https://www.youtube.com/watch?v=qDZ8lIDJfoA")
  })

  test("youtube_video_after_play_loads_privacy_enhanced_player", async () => {
    // Arrange
    const user = userEvent.setup()
    renderWithProviders(
      <YouTubeVideo
        title="Tutorial: cómo buscar creators en Kiizama"
        videoId="qDZ8lIDJfoA"
      />,
      { language: "es" },
    )

    // Act
    await user.click(
      screen.getByRole("button", {
        name: "Reproducir video: Tutorial: cómo buscar creators en Kiizama",
      }),
    )

    // Assert
    const player = screen.getByTitle(
      "Reproductor del video: Tutorial: cómo buscar creators en Kiizama",
    )
    expect(player).toHaveAttribute(
      "src",
      "https://www.youtube-nocookie.com/embed/qDZ8lIDJfoA?playsinline=1&rel=0",
    )
    expect(player).toHaveAttribute(
      "referrerpolicy",
      "strict-origin-when-cross-origin",
    )
    expect(player).toHaveAttribute("allowfullscreen")
  })
})
