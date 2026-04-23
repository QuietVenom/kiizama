import { Box, Flex, Heading, Text } from "@chakra-ui/react"
import { FiInfo } from "react-icons/fi"

import { Button } from "@/components/ui/button"

export const SearchHeader = ({ onOpenGuide }: { onOpenGuide: () => void }) => (
  <Flex
    mb={{ base: 7, lg: 8 }}
    alignItems={{ base: "flex-start", lg: "flex-start" }}
    justifyContent="space-between"
    gap={{ base: 4, lg: 6 }}
    direction={{ base: "column", lg: "row" }}
  >
    <Box flex="1" minW={0}>
      <Text textStyle="eyebrow">Creators Search</Text>
      <Heading
        mt={3}
        textStyle="pageTitle"
        fontSize={{ base: "3xl", lg: "4xl" }}
        fontWeight="black"
        lineHeight="1.05"
        maxW="24ch"
      >
        Search saved creator profiles in one request.
      </Heading>
      <Text
        mt={3}
        color="ui.secondaryText"
        fontSize={{ base: "md", lg: "lg" }}
        maxW="68ch"
      >
        Add multiple Instagram usernames, review which creators are already
        stored in the platform, and open a complete view for each match.
      </Text>
    </Box>

    <Button
      variant="outline"
      alignSelf={{ base: "stretch", lg: "flex-start" }}
      onClick={onOpenGuide}
    >
      <FiInfo />
      Search guide
    </Button>
  </Flex>
)
