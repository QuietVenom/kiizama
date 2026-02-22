import { Box, type BoxProps } from "@chakra-ui/react"

const InsightCard = (props: BoxProps) => {
  const { children, ...rest } = props

  return (
    <Box
      rounded="2xl"
      borderWidth="1px"
      borderColor="design.100"
      bg="white"
      p={{ base: 6, md: 8 }}
      boxShadow="lg"
      {...rest}
    >
      {children}
    </Box>
  )
}

export default InsightCard
