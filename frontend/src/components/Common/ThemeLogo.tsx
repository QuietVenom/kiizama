import type { ImageProps } from "@chakra-ui/react"
import { Image } from "@chakra-ui/react"
import { useColorMode } from "@/components/ui/color-mode"

type ThemeLogoProps = Omit<ImageProps, "src">

const ThemeLogo = (props: ThemeLogoProps) => {
  const { colorMode } = useColorMode()
  const logoSrc =
    colorMode === "dark"
      ? "/assets/images/noBgWhite.svg"
      : "/assets/images/noBgColor.svg"

  return (
    <Image
      src={logoSrc}
      alt="Kiizama logo"
      loading="eager"
      fetchPriority="high"
      decoding="async"
      display="block"
      {...props}
    />
  )
}

export default ThemeLogo
