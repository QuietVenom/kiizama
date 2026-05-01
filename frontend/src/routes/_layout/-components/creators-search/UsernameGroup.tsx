import { Badge, Box, Flex, Text } from "@chakra-ui/react"

export const UsernameGroup = ({
  title,
  tone,
  usernames,
}: {
  title: string
  tone: "success" | "danger" | "warning" | "neutral"
  usernames: string[]
}) => {
  const toneStyles =
    tone === "success"
      ? {
          borderColor: "ui.success",
          bg: "ui.successSoft",
          textColor: "ui.successText",
        }
      : tone === "danger"
        ? {
            borderColor: "ui.danger",
            bg: "ui.dangerSoft",
            textColor: "ui.dangerText",
          }
        : tone === "warning"
          ? {
              borderColor: "ui.warning",
              bg: "ui.warningSoft",
              textColor: "ui.warningText",
            }
          : {
              borderColor: "ui.border",
              bg: "ui.surfaceSoft",
              textColor: "ui.text",
            }

  return (
    <Box
      rounded="2xl"
      borderWidth="1px"
      borderColor={toneStyles.borderColor}
      bg={toneStyles.bg}
      px={4}
      py={4}
    >
      <Flex alignItems="center" justifyContent="space-between" gap={3}>
        <Text color={toneStyles.textColor} fontWeight="black">
          {title}
        </Text>
        <Badge
          rounded="full"
          borderWidth="1px"
          borderColor="ui.borderSoft"
          bg="ui.panel"
          color={toneStyles.textColor}
          px={3}
          py={1.5}
        >
          {usernames.length}
        </Badge>
      </Flex>

      {usernames.length === 0 ? (
        <Text mt={3} color="ui.secondaryText" fontSize="sm">
          No usernames in this group.
        </Text>
      ) : (
        <Flex mt={3} gap={2} wrap="wrap">
          {usernames.map((username) => (
            <Badge
              key={`${title}-${username}`}
              rounded="full"
              borderWidth="1px"
              borderColor="ui.borderSoft"
              bg="ui.panel"
              color="ui.text"
              px={3}
              py={1.5}
            >
              @{username}
            </Badge>
          ))}
        </Flex>
      )}
    </Box>
  )
}
