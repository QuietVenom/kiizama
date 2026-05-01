import { Box, Flex, Grid } from "@chakra-ui/react"

import {
  Skeleton,
  SkeletonCircle,
  SkeletonText,
} from "@/components/ui/skeleton"

export const ResultSkeletonCard = () => (
  <Box layerStyle="dashboardCard" p={{ base: 5, lg: 6 }}>
    <Flex gap={4}>
      <SkeletonCircle size="16" />
      <Box flex="1">
        <Skeleton height="5" maxW="220px" />
        <Skeleton height="4" mt={3} maxW="140px" />
        <SkeletonText mt={4} noOfLines={3} />
      </Box>
    </Flex>
    <Grid mt={6} templateColumns="repeat(3, minmax(0, 1fr))" gap={3}>
      <Skeleton height="16" rounded="2xl" />
      <Skeleton height="16" rounded="2xl" />
      <Skeleton height="16" rounded="2xl" />
    </Grid>
  </Box>
)
