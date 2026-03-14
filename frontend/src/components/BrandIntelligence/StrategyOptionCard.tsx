import { chakra, Flex, Icon, Text } from "@chakra-ui/react"
import type { IconType } from "react-icons"

type StrategyOptionCardProps = {
  description: string
  icon: IconType
  isActive: boolean
  onClick: () => void
  title: string
}

const StrategyOptionCard = ({
  description,
  icon,
  isActive,
  onClick,
  title,
}: StrategyOptionCardProps) => {
  return (
    <chakra.button
      type="button"
      layerStyle="dashboardCardInteractive"
      textAlign="left"
      p={{ base: 5, md: 6 }}
      borderColor={isActive ? "ui.brandBorderSoft" : "ui.border"}
      bg={isActive ? "ui.brandSoft" : "ui.panel"}
      onClick={onClick}
    >
      <Flex
        boxSize="11"
        alignItems="center"
        justifyContent="center"
        rounded="2xl"
        bg={isActive ? "ui.panel" : "ui.surfaceSoft"}
        color={isActive ? "ui.brandText" : "ui.link"}
      >
        <Icon as={icon} boxSize={5} />
      </Flex>
      <Text mt={4} fontSize={{ base: "lg", lg: "xl" }} fontWeight="black">
        {title}
      </Text>
      <Text mt={2} color="ui.secondaryText" fontSize="sm">
        {description}
      </Text>
    </chakra.button>
  )
}

export default StrategyOptionCard
