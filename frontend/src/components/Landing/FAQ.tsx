import {
  Box,
  Button,
  Container,
  Heading,
  Icon,
  Stack,
  Text,
} from "@chakra-ui/react"
import type { RefObject } from "react"
import { useState } from "react"
import { FiMinus, FiPlus } from "react-icons/fi"

const faqs = [
  {
    id: "platform-support",
    question: "Which social platform is supported today?",
    answer:
      "Kiizama currently focuses on Instagram workflows, including profile snapshots, report generation, and reputation strategy outputs.",
  },
  {
    id: "report-outputs",
    question: "What outputs does the platform generate?",
    answer:
      "You can generate HTML and PDF reports. Multi-profile requests can be delivered as a ZIP file containing each output.",
  },
  {
    id: "ai-enrichment",
    question: "Do you use AI in the analysis flow?",
    answer:
      "Yes. The platform enriches profiles with AI categories and roles, and powers campaign and creator reputation strategy generation.",
  },
  {
    id: "request-limits",
    question: "Are there operational limits per request?",
    answer:
      "Yes. Current limits are up to 10 usernames per scrape job, up to 20 usernames per Instagram report request, and up to 15 profiles per campaign strategy request.",
  },
]

type FAQProps = {
  sectionRef: RefObject<HTMLElement | null>
}

const FAQ = ({ sectionRef }: FAQProps) => {
  const [openItem, setOpenItem] = useState<string | null>(null)

  const handleToggle = (id: string) => {
    setOpenItem((current) => (current === id ? null : id))
  }

  return (
    // biome-ignore lint/correctness/useUniqueElementIds: section anchor is required for footer navigation links
    <Box
      ref={sectionRef}
      id="faq"
      as="section"
      scrollMarginTop="88px"
      py={{ base: 20, md: 24, lg: 28 }}
    >
      <Container maxW="4xl">
        <Stack textAlign="center" gap={4} mb={12}>
          <Text
            color="ui.link"
            textTransform="uppercase"
            fontWeight="bold"
            letterSpacing="0.12em"
            fontSize="xs"
            display="inline-flex"
            alignItems="center"
            justifyContent="center"
            gap={3}
          >
            <Box as="span" h="1px" w="8" bg="ui.mainHover" />
            FAQ
            <Box as="span" h="1px" w="8" bg="ui.mainHover" />
          </Text>
          <Heading
            size={{ base: "2xl", md: "3xl" }}
            color="ui.text"
            letterSpacing="-0.02em"
            fontFamily="'Plus Jakarta Sans', 'Avenir Next', 'Segoe UI', sans-serif"
          >
            Answers to key questions
          </Heading>
        </Stack>

        <Stack gap={4}>
          {faqs.map((item) => {
            const isOpen = openItem === item.id
            return (
              <Box
                key={item.id}
                layerStyle={isOpen ? "faqCardActive" : "faqCard"}
                overflow="hidden"
                transition="border-color 220ms ease, background-color 220ms ease, box-shadow 220ms ease"
              >
                <Button
                  variant="ghost"
                  w="full"
                  justifyContent="space-between"
                  px={{ base: 5, md: 6 }}
                  py={6}
                  h="auto"
                  _hover={{ bg: "transparent", color: "ui.link" }}
                  onClick={() => handleToggle(item.id)}
                >
                  <Text
                    textAlign="left"
                    fontWeight="bold"
                    color="ui.text"
                    fontSize={{ base: "md", md: "lg" }}
                  >
                    {item.question}
                  </Text>
                  <Icon
                    as={isOpen ? FiMinus : FiPlus}
                    boxSize={5}
                    color={isOpen ? "ui.link" : "ui.secondaryText"}
                  />
                </Button>

                <Box
                  px={{ base: 5, md: 6 }}
                  pb={isOpen ? 7 : 0}
                  display="grid"
                  gridTemplateRows={isOpen ? "1fr" : "0fr"}
                  opacity={isOpen ? 1 : 0}
                  transition="grid-template-rows 320ms cubic-bezier(0.22, 1, 0.36, 1), opacity 220ms ease, padding-bottom 220ms ease"
                >
                  <Box overflow="hidden">
                    <Text
                      color="ui.secondaryText"
                      fontSize={{ base: "sm", md: "md" }}
                      fontWeight="bold"
                      lineHeight="1.8"
                      transform={isOpen ? "translateY(0)" : "translateY(-6px)"}
                      transition="transform 260ms ease"
                    >
                      {item.answer}
                    </Text>
                  </Box>
                </Box>
              </Box>
            )
          })}
        </Stack>
      </Container>
    </Box>
  )
}

export default FAQ
