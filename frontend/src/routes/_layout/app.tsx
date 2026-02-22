import { Box, Grid, Text } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import { FiFileText, FiShield, FiTrendingUp, FiUserCheck } from "react-icons/fi"

import DashboardTopbar from "@/components/Dashboard/DashboardTopbar"
import MetricCard from "@/components/Dashboard/MetricCard"
import RecentProfileAnalysisCard from "@/components/Dashboard/RecentProfileAnalysisCard"
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
            label="Total Creators"
            value="1,284"
            trend="+12%"
            iconBg="#DBEAFE"
            iconColor="#2563EB"
          />
          <MetricCard
            icon={FiFileText}
            label="Active Reports"
            value="42"
            trend="+5"
            iconBg="#F3E8FF"
            iconColor="#9333EA"
          />
          <MetricCard
            icon={FiShield}
            label="Avg. Reputation"
            value="84/100"
            trend="+2%"
            iconBg="#D1FAE5"
            iconColor="#059669"
          />
          <MetricCard
            icon={FiTrendingUp}
            label="Trend Index"
            value="9.2"
            trend="Rising"
            iconBg="#FEF3C7"
            iconColor="#EA580C"
          />
        </Grid>

        <Grid templateColumns={{ base: "1fr", xl: "1.6fr 1fr" }} gap={6}>
          <RecentProfileAnalysisCard />
          <StrategicInsightCard />
        </Grid>
      </Box>
    </Box>
  )
}
