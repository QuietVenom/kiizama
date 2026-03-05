import {
  Box,
  Link as ChakraLink,
  Container,
  IconButton,
  Image,
  Input,
  Text,
} from "@chakra-ui/react"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { type SubmitHandler, useForm } from "react-hook-form"
import { FiLock, FiUser } from "react-icons/fi"

import type { UserRegister } from "@/client"
import InsightCard from "@/components/Common/InsightCard"
import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"
import { InputGroup } from "@/components/ui/input-group"
import { PasswordInput } from "@/components/ui/password-input"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { isPublicFeatureFlagEnabled } from "@/hooks/useFeatureFlags"
import {
  confirmPasswordRules,
  emailPattern,
  getWwwUrl,
  passwordRules,
} from "@/utils"
import Logo from "/assets/images/noBgColor.svg"
import SymbolLogo from "/assets/images/symbol.svg"

const FORM_CONTAINER_MAX_W = { base: "md", md: "3xl" } as const
const FORM_CARD_MIN_H = { base: "auto", md: "560px" } as const
const FORM_CONTROL_MAX_W = { base: "full", md: "50%" } as const
const WAITING_LIST_FLAG_KEY = "waiting-list"

export const Route = createFileRoute("/signup")({
  component: SignUp,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/app",
      })
    }

    let isWaitingListEnabled = false
    try {
      isWaitingListEnabled = await isPublicFeatureFlagEnabled(
        WAITING_LIST_FLAG_KEY,
      )
    } catch {
      // If flag fetch fails, keep signup available.
    }

    if (isWaitingListEnabled) {
      throw redirect({
        to: "/waiting-list",
      })
    }
  },
})

interface UserRegisterForm extends UserRegister {
  confirm_password: string
}

function SignUp() {
  const { signUpMutation } = useAuth()
  const landingUrl = getWwwUrl("/")
  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<UserRegisterForm>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      email: "",
      full_name: "",
      password: "",
      confirm_password: "",
    },
  })

  const onSubmit: SubmitHandler<UserRegisterForm> = (data) => {
    signUpMutation.mutate(data)
  }

  return (
    <Box
      minH="100vh"
      position="relative"
      overflow="hidden"
      bgGradient="linear(to-b, #FFFDF8, #FFF9ED 48%, white)"
    >
      <Box
        position="absolute"
        top="-24"
        right="-20"
        w={{ base: "64", md: "88" }}
        h={{ base: "64", md: "88" }}
        rounded="full"
        bg="orange.100"
        opacity={0.5}
        filter="blur(100px)"
      />
      <Box
        position="absolute"
        top="20%"
        left="-20"
        w={{ base: "52", md: "68" }}
        h={{ base: "52", md: "68" }}
        rounded="full"
        bg="orange.50"
        opacity={0.8}
        filter="blur(90px)"
      />

      <ChakraLink
        href={landingUrl}
        style={{ position: "fixed", top: "1rem", right: "1rem", zIndex: 20 }}
      >
        <IconButton
          aria-label="Go to landing page"
          bg="white"
          color="orange.500"
          borderWidth="1px"
          borderColor="orange.100"
          rounded="full"
          boxShadow="sm"
          _hover={{ bg: "orange.50" }}
        >
          <Image src={SymbolLogo} alt="Kiizama symbol" boxSize="5" />
        </IconButton>
      </ChakraLink>
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
          gap={4}
          rounded="3xl"
          borderColor="gray.100"
          boxShadow="0 16px 34px rgba(15, 23, 42, 0.06)"
        >
          <Image
            src={Logo}
            alt="Kiizama logo"
            height="auto"
            w={{ base: "368px", md: "416px" }}
            objectFit="contain"
            alignSelf="center"
            mb={4}
          />
          <Field
            w={FORM_CONTROL_MAX_W}
            invalid={!!errors.full_name}
            errorText={errors.full_name?.message}
          >
            <InputGroup w="100%" startElement={<FiUser />}>
              <Input
                minLength={3}
                {...register("full_name", {
                  required: "Full Name is required",
                })}
                placeholder="Full Name"
                type="text"
              />
            </InputGroup>
          </Field>

          <Field
            w={FORM_CONTROL_MAX_W}
            invalid={!!errors.email}
            errorText={errors.email?.message}
          >
            <InputGroup w="100%" startElement={<FiUser />}>
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
          <Box w={FORM_CONTROL_MAX_W}>
            <PasswordInput
              type="password"
              startElement={<FiLock />}
              {...register("password", passwordRules())}
              placeholder="Password"
              errors={errors}
            />
          </Box>
          <Box w={FORM_CONTROL_MAX_W}>
            <PasswordInput
              type="confirm_password"
              startElement={<FiLock />}
              {...register("confirm_password", confirmPasswordRules(getValues))}
              placeholder="Confirm Password"
              errors={errors}
            />
          </Box>
          <Button
            w={FORM_CONTROL_MAX_W}
            variant="solid"
            type="submit"
            loading={isSubmitting}
          >
            Sign Up
          </Button>
          <Text w={FORM_CONTROL_MAX_W} textAlign="center">
            Already have an account?{" "}
            <RouterLink to="/login" className="main-link">
              Log In
            </RouterLink>
          </Text>
        </InsightCard>
      </Container>
    </Box>
  )
}
