import { Box } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import { useRef } from "react"
import FAQ from "@/components/Landing/FAQ"
import Features from "@/components/Landing/Features"
import Footer from "@/components/Landing/Footer"
import Hero from "@/components/Landing/Hero"
import LandingNavbar from "@/components/Landing/Navbar"
import Pricing from "@/components/Landing/Pricing"
import { fetchPublicFeatureFlag } from "@/hooks/useFeatureFlags"

const WAITING_LIST_FLAG_KEY = "waiting-list"

export const Route = createFileRoute("/")({
  loader: async () => {
    try {
      const featureFlag = await fetchPublicFeatureFlag(WAITING_LIST_FLAG_KEY)
      return {
        isWaitingListEnabled: Boolean(
          featureFlag?.is_public && featureFlag.is_enabled,
        ),
      }
    } catch {
      return { isWaitingListEnabled: false }
    }
  },
  component: LandingPage,
})

function LandingPage() {
  const { isWaitingListEnabled } = Route.useLoaderData()
  const navbarRef = useRef<HTMLElement | null>(null)
  const homeSectionRef = useRef<HTMLElement | null>(null)
  const featuresSectionRef = useRef<HTMLElement | null>(null)
  const pricingSectionRef = useRef<HTMLElement | null>(null)
  const faqSectionRef = useRef<HTMLElement | null>(null)

  const sectionRefs = {
    home: homeSectionRef,
    features: featuresSectionRef,
    pricing: pricingSectionRef,
    faq: faqSectionRef,
  }

  return (
    <Box bg="ui.page" minH="100vh">
      <LandingNavbar
        isWaitingListEnabled={isWaitingListEnabled}
        navbarRef={navbarRef}
        sectionRefs={sectionRefs}
      />
      <Hero
        isWaitingListEnabled={isWaitingListEnabled}
        sectionRef={homeSectionRef}
      />
      <Features sectionRef={featuresSectionRef} />
      <Pricing
        isWaitingListEnabled={isWaitingListEnabled}
        sectionRef={pricingSectionRef}
      />
      <FAQ sectionRef={faqSectionRef} />
      <Footer isWaitingListEnabled={isWaitingListEnabled} />
    </Box>
  )
}
