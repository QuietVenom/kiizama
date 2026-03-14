import { Badge, Box, Flex, Heading, SimpleGrid, Text } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import { useMemo, useState } from "react"
import { useForm, useWatch } from "react-hook-form"
import { FiTarget, FiUserCheck } from "react-icons/fi"
import { ImBlocked } from "react-icons/im"

import CampaignStrategyBuilder from "@/components/BrandIntelligence/CampaignStrategyBuilder"
import CreatorStrategyBuilder from "@/components/BrandIntelligence/CreatorStrategyBuilder"
import StrategyOptionCard from "@/components/BrandIntelligence/StrategyOptionCard"
import DashboardTopbar from "@/components/Dashboard/DashboardTopbar"
import {
  type CampaignFormValues,
  type CreatorFormValues,
  campaignFormDefaultValues,
  creatorFormDefaultValues,
  creatorTextInputDefaultValues,
} from "@/features/brand-intelligence/form-values"
import { useProfileExistenceValidation } from "@/features/brand-intelligence/use-profile-existence-validation"
import { normalizeUsernameList } from "@/features/brand-intelligence/utils"

export const Route = createFileRoute("/_layout/brand-intelligence")({
  component: BrandIntelligencePage,
})

type StrategyType =
  | "reputation-campaign-strategy"
  | "reputation-creator-strategy"

const EMPTY_USERNAMES: string[] = []

function BrandIntelligencePage() {
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyType>(
    "reputation-campaign-strategy",
  )
  const [creatorTextInputValues, setCreatorTextInputValues] = useState(
    creatorTextInputDefaultValues,
  )

  const campaignForm = useForm<CampaignFormValues>({
    mode: "onBlur",
    shouldUnregister: false,
    defaultValues: campaignFormDefaultValues,
  })
  const creatorForm = useForm<CreatorFormValues>({
    mode: "onBlur",
    shouldUnregister: false,
    defaultValues: creatorFormDefaultValues,
  })

  const campaignProfilesValue = useWatch({
    control: campaignForm.control,
    name: "profiles_list",
    defaultValue: campaignFormDefaultValues.profiles_list,
  })
  const creatorUsernameValue = useWatch({
    control: creatorForm.control,
    name: "creator_username",
    defaultValue: creatorFormDefaultValues.creator_username,
  })

  const normalizedCampaignProfiles = useMemo(
    () => normalizeUsernameList(campaignProfilesValue ?? []),
    [campaignProfilesValue],
  )
  const normalizedCreatorUsername = useMemo(
    () => normalizeUsernameList([creatorUsernameValue ?? ""])[0] ?? "",
    [creatorUsernameValue],
  )
  const creatorValidationUsernames = useMemo(
    () =>
      normalizedCreatorUsername ? [normalizedCreatorUsername] : EMPTY_USERNAMES,
    [normalizedCreatorUsername],
  )

  const campaignValidation = useProfileExistenceValidation(
    normalizedCampaignProfiles,
  )
  const creatorValidation = useProfileExistenceValidation(
    creatorValidationUsernames,
  )

  return (
    <Box minH="100vh" bg="ui.page">
      <DashboardTopbar />

      <Box px={{ base: 4, md: 7, lg: 10 }} py={{ base: 7, lg: 9 }}>
        <Flex
          mb={{ base: 7, lg: 8 }}
          alignItems={{ base: "flex-start", lg: "flex-start" }}
          justifyContent="space-between"
          gap={{ base: 4, lg: 6 }}
          direction={{ base: "column", lg: "row" }}
        >
          <Box flex="1" minW={0}>
            <Text textStyle="eyebrow">Brand Intelligence</Text>
            <Heading
              mt={3}
              textStyle="pageTitle"
              fontSize={{ base: "3xl", lg: "4xl" }}
              fontWeight="black"
              lineHeight="1.05"
              maxW="18ch"
            >
              Build modular reputation strategy reports.
            </Heading>
            <Text
              mt={3}
              color="ui.secondaryText"
              fontSize={{ base: "md", lg: "lg" }}
              maxW="70ch"
            >
              Start with influencer usernames, validate them against Mining, and
              then generate the selected reputation strategy as a PDF report.
            </Text>
          </Box>

          <Flex
            gap={2}
            wrap="wrap"
            alignSelf={{ base: "stretch", lg: "flex-start" }}
          >
            <Badge
              rounded="full"
              bg="ui.brandSoft"
              color="ui.brandText"
              px={3}
              py={1.5}
            >
              Mining validation first
            </Badge>
            <Badge
              rounded="full"
              bg="ui.surfaceSoft"
              color="ui.secondaryText"
              px={3}
              py={1.5}
            >
              PDF only
            </Badge>
            <Badge
              rounded="full"
              bg="ui.surfaceSoft"
              color="ui.secondaryText"
              px={3}
              py={1.5}
            >
              Local reports synced
            </Badge>
          </Flex>
        </Flex>

        <SimpleGrid
          columns={{ base: 1, xl: 2 }}
          gap={5}
          mb={{ base: 7, lg: 8 }}
        >
          <StrategyOptionCard
            description="Validate a list of influencers first, then generate a reputation campaign strategy around the selected campaign model."
            icon={FiTarget}
            isActive={selectedStrategy === "reputation-campaign-strategy"}
            onClick={() => setSelectedStrategy("reputation-campaign-strategy")}
            title="Reputation Campaign Strategy"
          />
          <StrategyOptionCard
            description="Validate the creator profile first, then generate a creator-centered reputation strategy with signals, platforms, and collaborators."
            icon={FiUserCheck}
            isActive={selectedStrategy === "reputation-creator-strategy"}
            onClick={() => setSelectedStrategy("reputation-creator-strategy")}
            title="Reputation Creator Strategy"
          />
        </SimpleGrid>

        <Box
          mb={{ base: 6, lg: 7 }}
          rounded="3xl"
          borderWidth="1px"
          borderColor="ui.border"
          bg="ui.panel"
          px={{ base: 5, md: 6 }}
          py={{ base: 5, md: 6 }}
        >
          <Flex alignItems="flex-start" gap={3}>
            <Flex
              boxSize="10"
              flexShrink={0}
              alignItems="center"
              justifyContent="center"
              rounded="2xl"
              bg="ui.brandSoft"
              color="ui.brandText"
            >
              <ImBlocked />
            </Flex>
            <Box>
              <Text fontWeight="black">Validation gate is mandatory</Text>
              <Text mt={1} color="ui.secondaryText">
                Before any report is generated, the flow always re-runs{" "}
                <Text as="span" fontWeight="bold" color="inherit">
                  the profiles existence
                </Text>
                . Missing usernames block report generation, profiles with
                update needed are allowed with a visible warning, and successful
                PDFs are stored in local storage for the dashboard.
              </Text>
            </Box>
          </Flex>
        </Box>

        {selectedStrategy === "reputation-campaign-strategy" ? (
          <CampaignStrategyBuilder
            form={campaignForm}
            normalizedProfiles={normalizedCampaignProfiles}
            validation={campaignValidation}
          />
        ) : (
          <CreatorStrategyBuilder
            creatorTextInputValues={creatorTextInputValues}
            creatorUsername={normalizedCreatorUsername}
            creatorValidationUsernames={creatorValidationUsernames}
            form={creatorForm}
            onTextInputValuesChange={setCreatorTextInputValues}
            validation={creatorValidation}
          />
        )}
      </Box>
    </Box>
  )
}
