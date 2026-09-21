import { Box, Button, chakra, Icon, Link, Stack, Text } from "@chakra-ui/react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { FiExternalLink, FiPlay } from "react-icons/fi"

type YouTubeVideoProps = {
  title: string
  videoId: string
}

const buildYouTubeEmbedUrl = (videoId: string) =>
  `https://www.youtube-nocookie.com/embed/${videoId}?playsinline=1&rel=0`

const buildYouTubeWatchUrl = (videoId: string) =>
  `https://www.youtube.com/watch?v=${videoId}`

const YouTubeVideo = ({ title, videoId }: YouTubeVideoProps) => {
  const { t } = useTranslation("landing")
  const [isLoaded, setIsLoaded] = useState(false)
  const playerTitle = t("blog.video.playerTitle", { title })

  return (
    <Stack gap={4}>
      <Box
        aspectRatio={16 / 9}
        overflow="hidden"
        rounded={{ base: "2xl", md: "3xl" }}
        borderWidth="1px"
        borderColor="ui.brandBorderSoft"
        bg="ui.panelInverse"
        boxShadow="ui.card"
      >
        {isLoaded ? (
          <chakra.iframe
            src={buildYouTubeEmbedUrl(videoId)}
            title={playerTitle}
            width="100%"
            height="100%"
            border="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
            referrerPolicy="strict-origin-when-cross-origin"
          />
        ) : (
          <Button
            type="button"
            aria-label={t("blog.video.playLabel", { title })}
            onClick={() => setIsLoaded(true)}
            width="full"
            height="full"
            rounded="none"
            color="ui.textInverse"
            bg="ui.panelInverse"
            backgroundImage="radial-gradient(circle at 50% 35%, rgba(118, 90, 255, 0.34), transparent 48%)"
            _hover={{ bg: "ui.panelInverse", color: "ui.textInverse" }}
            _focusVisible={{ outline: "3px solid", outlineColor: "ui.link" }}
          >
            <Stack align="center" gap={4} px={6} textAlign="center">
              <Box
                display="inline-flex"
                alignItems="center"
                justifyContent="center"
                boxSize={{ base: 14, md: 16 }}
                rounded="full"
                bg="ui.link"
                boxShadow="0 12px 32px rgba(0, 0, 0, 0.3)"
              >
                <Icon as={FiPlay} boxSize={{ base: 6, md: 7 }} ms={1} />
              </Box>
              <Stack gap={1}>
                <Text fontSize={{ base: "lg", md: "xl" }} fontWeight="black">
                  {t("blog.video.play")}
                </Text>
                <Text
                  color="ui.inverseMutedText"
                  fontSize={{ base: "sm", md: "md" }}
                  whiteSpace="normal"
                >
                  {t("blog.video.privacyNotice")}
                </Text>
              </Stack>
            </Stack>
          </Button>
        )}
      </Box>

      <Link
        href={buildYouTubeWatchUrl(videoId)}
        target="_blank"
        rel="noopener noreferrer"
        alignSelf="flex-start"
        display="inline-flex"
        alignItems="center"
        gap={2}
        color="ui.link"
        fontWeight="bold"
        textDecoration="underline"
        textUnderlineOffset="0.18em"
      >
        {t("blog.video.watchOnYouTube")}
        <FiExternalLink aria-hidden="true" />
      </Link>
    </Stack>
  )
}

export default YouTubeVideo
