import { Box, Grid, Text } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import { FiFileText, FiShield, FiUserCheck } from "react-icons/fi"

import DashboardTopbar from "@/components/Dashboard/DashboardTopbar"
import MetricCard from "@/components/Dashboard/MetricCard"
import RecentReportsCard from "@/components/Dashboard/RecentReportsCard"
import StrategicInsightCard from "@/components/Dashboard/StrategicInsightCard"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/app")({
  component: Home,
})

function Home() {
  const { user: currentUser } = useAuth()
  const displayName = currentUser?.full_name || currentUser?.email || "there"

  return (
    <Box minH="100vh" bg="ui.page">
      <DashboardTopbar />

      <Box px={{ base: 4, md: 7, lg: 10 }} py={{ base: 7, lg: 9 }}>
        <Box mb={{ base: 7, lg: 8 }}>
          <Text
            fontSize={{ base: "2xl", md: "3xl", lg: "4xl" }}
            fontWeight="black"
            letterSpacing="-0.03em"
            lineHeight="1.05"
            truncate
            maxW="32ch"
          >
            Hi, {displayName} 👋
          </Text>
          <Text
            mt={3}
            color="ui.secondaryText"
            fontSize={{ base: "md", lg: "lg" }}
            fontWeight="medium"
            maxW="50ch"
          >
            Welcome back, nice to see you again! Here's what's happening today.
          </Text>
        </Box>

        <Grid
          templateColumns={{
            base: "1fr",
            md: "repeat(2, 1fr)",
            xl: "repeat(4, 1fr)",
          }}
          gap={5}
          mb={{ base: 7, lg: 8 }}
        >
          <MetricCard
            icon={FiUserCheck}
            label="Profile Mining: Total Credits"
            value="50 / 50"
            tone="info"
          />
          <MetricCard
            icon={FiFileText}
            label="Creator Report: Social Media Reports"
            value="20 / 20"
            tone="accent"
          />
          <MetricCard
            icon={FiShield}
            label="Reputation Campaign Strategy: Created Reports"
            value="3 / 3"
            tone="positive"
          />
          <MetricCard
            icon={FiShield}
            label="Reputation Creator Strategy: Created Reports"
            value="3 / 3"
            tone="accent"
          />
        </Grid>

        <Grid templateColumns={{ base: "1fr", xl: "1.6fr 1fr" }} gap={6}>
          <RecentReportsCard />
          <StrategicInsightCard />
        </Grid>
      </Box>
    </Box>
  )
}
