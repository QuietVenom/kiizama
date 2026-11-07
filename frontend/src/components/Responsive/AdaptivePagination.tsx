import { Box, Flex } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"
import {
  PaginationItems,
  PaginationNextTrigger,
  PaginationPageText,
  PaginationPrevTrigger,
  PaginationRoot,
  type PaginationRootProps,
} from "@/components/ui/pagination"

export function AdaptivePagination(props: PaginationRootProps) {
  const { t } = useTranslation("common")
  return (
    <Box minW={0} w="full" css={{ containerType: "inline-size" }}>
      <PaginationRoot
        {...props}
        aria-label={t("pagination.navigation")}
        w="full"
        minW={0}
      >
        <Flex align="center" justify="center" gap={2} minW={0}>
          <PaginationPrevTrigger aria-label={t("pagination.previous")} />
          <Box
            display="none"
            css={{ "@container (min-width: 38rem)": { display: "flex" } }}
          >
            <PaginationItems />
          </Box>
          <PaginationPageText fontSize="sm" textAlign="center" />
          <PaginationNextTrigger aria-label={t("pagination.next")} />
        </Flex>
      </PaginationRoot>
    </Box>
  )
}
