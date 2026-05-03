import { Badge, Box, Flex, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"

type StrategySummaryValue = string | string[] | null | undefined

type StrategySummarySection = {
  items: Array<{
    label: string
    value: StrategySummaryValue
  }>
  title: string
}

type StrategySummaryCardProps = {
  sections: StrategySummarySection[]
  title: string
}

const hasRenderableValue = (value: StrategySummaryValue) => {
  if (Array.isArray(value)) {
    return value.length > 0
  }

  return Boolean(value)
}

const StrategySummaryCard = ({ sections, title }: StrategySummaryCardProps) => {
  const { t } = useTranslation("brandIntelligence")
  const visibleSections = sections
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => hasRenderableValue(item.value)),
    }))
    .filter((section) => section.items.length > 0)

  return (
    <Box
      layerStyle="dashboardCard"
      p={{ base: 5, md: 6 }}
      position={{ xl: "sticky" }}
      top={{ xl: 24 }}
    >
      <Text textStyle="eyebrow">{t("summary.eyebrow")}</Text>
      <Text mt={2} fontSize={{ base: "xl", lg: "2xl" }} fontWeight="black">
        {title}
      </Text>
      <Text mt={2} color="ui.secondaryText">
        {t("summary.description")}
      </Text>

      {visibleSections.length === 0 ? (
        <Box
          mt={5}
          rounded="2xl"
          borderWidth="1px"
          borderColor="ui.border"
          bg="ui.surfaceSoft"
          px={4}
          py={5}
        >
          <Text fontWeight="bold">{t("summary.empty.title")}</Text>
          <Text mt={1.5} color="ui.secondaryText">
            {t("summary.empty.description")}
          </Text>
        </Box>
      ) : (
        <Flex mt={5} direction="column" gap={4}>
          {visibleSections.map((section) => (
            <Box
              key={section.title}
              rounded="2xl"
              borderWidth="1px"
              borderColor="ui.border"
              bg="ui.surfaceSoft"
              px={4}
              py={4}
            >
              <Text
                fontSize="xs"
                fontWeight="bold"
                letterSpacing="0.08em"
                textTransform="uppercase"
                color="ui.mutedText"
              >
                {section.title}
              </Text>
              <Flex mt={3} direction="column" gap={3}>
                {section.items.map((item) => (
                  <Box key={item.label}>
                    <Text fontSize="sm" fontWeight="bold">
                      {item.label}
                    </Text>
                    {Array.isArray(item.value) ? (
                      <Flex mt={2} gap={2} wrap="wrap">
                        {item.value.map((entry) => (
                          <Badge
                            key={`${item.label}-${entry}`}
                            rounded="full"
                            bg="ui.panel"
                            color="ui.secondaryText"
                            px={3}
                            py={1.5}
                            borderWidth="1px"
                            borderColor="ui.border"
                          >
                            {entry}
                          </Badge>
                        ))}
                      </Flex>
                    ) : (
                      <Text mt={1.5} color="ui.secondaryText">
                        {item.value}
                      </Text>
                    )}
                  </Box>
                ))}
              </Flex>
            </Box>
          ))}
        </Flex>
      )}
    </Box>
  )
}

export default StrategySummaryCard
