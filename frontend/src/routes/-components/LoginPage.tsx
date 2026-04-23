import {
  Box,
  Link as ChakraLink,
  Container,
  IconButton,
  Image,
  Input,
  Text,
} from "@chakra-ui/react"
import { Link as RouterLink } from "@tanstack/react-router"
import { type SubmitHandler, useForm } from "react-hook-form"
import { FiLock, FiMail } from "react-icons/fi"

import type { Body_login_login_access_token as AccessToken } from "@/client"
import InsightCard from "@/components/Common/InsightCard"
import ThemeLogo from "@/components/Common/ThemeLogo"
import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"
import { InputGroup } from "@/components/ui/input-group"
import { PasswordInput } from "@/components/ui/password-input"
import { getReturnToFromHref } from "@/features/errors/navigation"
import useAuth from "@/hooks/useAuth"
import { emailPattern, passwordRules } from "@/utils"
import SymbolLogo from "/assets/images/symbol.svg"

const FORM_CONTAINER_MAX_W = { base: "md", md: "3xl" } as const
const FORM_CARD_MIN_H = { base: "auto", md: "560px" } as const
const FORM_CONTROL_MAX_W = { base: "full", md: "50%" } as const

export function LoginPage() {
  const redirect =
    typeof window === "undefined"
      ? undefined
      : getReturnToFromHref(window.location.href)
  const { loginMutation, error, resetError } = useAuth(redirect)
  const landingUrl = "/"
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, dirtyFields, isSubmitted },
  } = useForm<AccessToken>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      username: "",
      password: "",
    },
  })
  const showUsernameError =
    !!errors.username && (dirtyFields.username || isSubmitted)
  const showPasswordError =
    !!errors.password && (dirtyFields.password || isSubmitted)

  const onSubmit: SubmitHandler<AccessToken> = async (data) => {
    if (isSubmitting) return

    resetError()

    try {
      await loginMutation.mutateAsync(data)
    } catch {
      // error is handled by useAuth hook
    }
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
        <ChakraLink href={landingUrl}>
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
        </ChakraLink>
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
          <Field
            w={FORM_CONTROL_MAX_W}
            invalid={showUsernameError || !!error}
            errorText={showUsernameError ? errors.username?.message : error}
          >
            <InputGroup w="100%" startElement={<FiMail />}>
              <Input
                {...register("username", {
                  required: "Username is required",
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
              showError={showPasswordError}
            />
          </Box>
          <Box w={FORM_CONTROL_MAX_W} textAlign="center">
            <RouterLink to="/recover-password" className="main-link">
              Forgot Password?
            </RouterLink>
          </Box>
          <Button
            w={FORM_CONTROL_MAX_W}
            layerStyle="brandGradientButton"
            type="submit"
            loading={isSubmitting}
            size="md"
          >
            Log In
          </Button>
          <Text w={FORM_CONTROL_MAX_W} textAlign="center">
            Don't have an account?{" "}
            <RouterLink to="/signup" className="main-link">
              Sign Up
            </RouterLink>
          </Text>
        </InsightCard>
      </Container>
    </Box>
  )
}
