import {
  Box,
  Container,
  chakra,
  IconButton,
  Image,
  Input,
  Text,
} from "@chakra-ui/react"
import { useMutation } from "@tanstack/react-query"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { type SubmitHandler, useForm } from "react-hook-form"
import { FiMail } from "react-icons/fi"

import { OpenAPI } from "@/client"
import InsightCard from "@/components/Common/InsightCard"
import ThemeLogo from "@/components/Common/ThemeLogo"
import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"
import { InputGroup } from "@/components/ui/input-group"
import { isLoggedIn } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { emailPattern } from "@/utils"
import SymbolLogo from "/assets/images/symbol.svg"

const FORM_CONTAINER_MAX_W = { base: "md", md: "3xl" } as const
const FORM_CARD_MIN_H = { base: "auto", md: "560px" } as const
const WAITING_LIST_CONTROL_W = { base: "full", md: "70%" } as const

type WaitingListInterest =
  | "public_relations"
  | "marketing"
  | "creator"
  | "creator_talent_management"
  | "publicity"
  | "other"

interface WaitingListForm {
  interest: WaitingListInterest | ""
  email: string
}

const WAITING_LIST_OPTIONS: Array<{
  value: WaitingListInterest
  label: string
}> = [
  {
    value: "public_relations",
    label: "Public Relations - Relaciones Publicas",
  },
  { value: "marketing", label: "Marketing - Marketing" },
  { value: "creator", label: "Creator - Creador" },
  {
    value: "creator_talent_management",
    label: "Creator/Talent Management - Gestion de Creadores/Talento",
  },
  { value: "publicity", label: "Publicity - Publicidad" },
  { value: "other", label: "Other - Otro" },
]

const WAITING_LIST_PATH = "/api/v1/public/waiting-list/"

export const Route = createFileRoute("/waiting-list")({
  component: WaitingList,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/app",
      })
    }
  },
})

function WaitingList() {
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<WaitingListForm>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      interest: "",
      email: "",
    },
  })

  const waitingListMutation = useMutation({
    mutationFn: async (data: WaitingListForm) => {
      const response = await fetch(`${OpenAPI.BASE}${WAITING_LIST_PATH}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          interest: data.interest,
          email: data.email,
        }),
      })

      const body = (await response.json()) as {
        detail?: string | Array<{ msg?: string }>
        message?: string
      }
      if (!response.ok) {
        const detail = body.detail
        if (Array.isArray(detail) && detail.length > 0) {
          throw new Error(detail[0]?.msg || "Something went wrong.")
        }
        throw new Error((detail as string) || "Something went wrong.")
      }
      return (
        body.message ||
        "Registro recibido. Gracias por unirte a la waiting list."
      )
    },
    onSuccess: (message: string) => {
      showSuccessToast(message)
      reset()
    },
    onError: (error: Error) => {
      showErrorToast(error.message || "Something went wrong.")
    },
  })

  const onSubmit: SubmitHandler<WaitingListForm> = async (data) => {
    await waitingListMutation.mutateAsync(data)
  }

  return (
    <Box
      minH="100vh"
      position="relative"
      overflow="hidden"
      layerStyle="publicPage"
    >
      <Box
        position="absolute"
        top="-24"
        right="-20"
        w={{ base: "64", md: "88" }}
        h={{ base: "64", md: "88" }}
        layerStyle="publicGlowPrimary"
      />
      <Box
        position="absolute"
        top="20%"
        left="-20"
        w={{ base: "52", md: "68" }}
        h={{ base: "52", md: "68" }}
        layerStyle="publicGlowSecondary"
      />

      <Box position="fixed" top="1rem" right="1rem" zIndex={20}>
        <RouterLink to="/">
          <IconButton
            aria-label="Go to landing page"
            bg="ui.panel"
            color="ui.brandText"
            borderWidth="1px"
            borderColor="ui.brandBorderSoft"
            rounded="full"
            boxShadow="ui.panelSm"
            _hover={{ bg: "ui.brandSoft" }}
          >
            <Image src={SymbolLogo} alt="Kiizama symbol" boxSize="5" />
          </IconButton>
        </RouterLink>
      </Box>
      <Container
        minH="100vh"
        maxW={FORM_CONTAINER_MAX_W}
        display="flex"
        alignItems="center"
        justifyContent="center"
        position="relative"
      >
        <InsightCard
          as="form"
          onSubmit={handleSubmit(onSubmit)}
          w="full"
          minH={FORM_CARD_MIN_H}
          px={{ base: 7, md: 10 }}
          py={{ base: 8, md: 10 }}
          display="flex"
          flexDir="column"
          alignItems="center"
          justifyContent="center"
          overflow="hidden"
          gap={4}
          rounded="3xl"
        >
          <ThemeLogo
            height="auto"
            w={{ base: "368px", md: "416px" }}
            objectFit="contain"
            alignSelf="center"
            mb={4}
          />
          <Text
            w={WAITING_LIST_CONTROL_W}
            fontSize="xl"
            fontWeight="semibold"
            textAlign="center"
          >
            Join Our Waiting List
          </Text>

          <Field
            w={WAITING_LIST_CONTROL_W}
            minW={0}
            maxW="100%"
            invalid={!!errors.interest}
            errorText={errors.interest?.message}
          >
            <chakra.select
              w="full"
              minW={0}
              maxW="100%"
              borderWidth="1px"
              borderColor={errors.interest ? "ui.danger" : "ui.borderSoft"}
              borderRadius="md"
              h="10"
              px={3}
              pr={10}
              bg="ui.panel"
              color="ui.text"
              fontSize={{ base: "sm", md: "md" }}
              overflow="hidden"
              textOverflow="ellipsis"
              whiteSpace="nowrap"
              {...register("interest", {
                required: "Please select an option",
              })}
            >
              <option value="">Select your area</option>
              {WAITING_LIST_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </chakra.select>
          </Field>

          <Field
            w={WAITING_LIST_CONTROL_W}
            minW={0}
            maxW="100%"
            invalid={!!errors.email}
            errorText={errors.email?.message}
          >
            <InputGroup w="100%" startElement={<FiMail />}>
              <Input
                {...register("email", {
                  required: "Email is required",
                  pattern: emailPattern,
                })}
                placeholder="Email"
                type="email"
              />
            </InputGroup>
          </Field>

          <Button
            w={WAITING_LIST_CONTROL_W}
            maxW="100%"
            layerStyle="brandGradientButton"
            type="submit"
            loading={isSubmitting || waitingListMutation.isPending}
          >
            Send
          </Button>
        </InsightCard>
      </Container>
    </Box>
  )
}
