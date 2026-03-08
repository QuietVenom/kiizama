import { Box, type BoxProps } from "@chakra-ui/react"

const InsightCard = (props: BoxProps) => {
  const { children, ...rest } = props

  return (
    <Box layerStyle="infoCard" rounded="2xl" p={{ base: 6, md: 8 }} {...rest}>
      {children}
    </Box>
  )
}

export default InsightCard
