import {
  Box,
  Link as ChakraLink,
  Container,
  Heading,
  IconButton,
  Image,
  Input,
  Text,
} from "@chakra-ui/react"
import { useMutation } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { type SubmitHandler, useForm } from "react-hook-form"
import { FiMail } from "react-icons/fi"

import { type ApiError, LoginService } from "@/client"
import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"
import { InputGroup } from "@/components/ui/input-group"
import { ensureValidStoredSession } from "@/features/auth/session"
import useCustomToast from "@/hooks/useCustomToast"
import { emailPattern, handleError } from "@/utils"
import SymbolLogo from "/assets/images/symbol.svg"

interface FormData {
  email: string
}

export const Route = createFileRoute("/recover-password")({
  component: RecoverPassword,
  beforeLoad: async () => {
    if (await ensureValidStoredSession()) {
      throw redirect({
        to: "/overview",
      })
    }
  },
})

function RecoverPassword() {
  const landingUrl = "/"
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>()
  const { showSuccessToast } = useCustomToast()

  const recoverPassword = async (data: FormData) => {
    await LoginService.recoverPassword({
      email: data.email,
    })
  }

  const mutation = useMutation({
    mutationFn: recoverPassword,
    onSuccess: () => {
      showSuccessToast("Password recovery email sent successfully.")
      reset()
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const onSubmit: SubmitHandler<FormData> = async (data) => {
    mutation.mutate(data)
  }

  return (
    <Box minH="100vh" position="relative">
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
        as="form"
        onSubmit={handleSubmit(onSubmit)}
        h="100vh"
        maxW="sm"
        alignItems="stretch"
        justifyContent="center"
        gap={4}
        centerContent
      >
        <Heading size="xl" color="ui.main" textAlign="center" mb={2}>
          Password Recovery
        </Heading>
        <Text textAlign="center">
          A password recovery email will be sent to the registered account.
        </Text>
        <Field invalid={!!errors.email} errorText={errors.email?.message}>
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
        <Button variant="solid" type="submit" loading={isSubmitting}>
          Continue
        </Button>
      </Container>
    </Box>
  )
}
