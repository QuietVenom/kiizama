import {
  Box,
  Link as ChakraLink,
  Heading,
  Stack,
  Table,
  Text,
} from "@chakra-ui/react"
import { createFileRoute, Link as RouterLink } from "@tanstack/react-router"
import { useEffect } from "react"
import InfoPageShell from "@/components/Common/InfoPageShell"

const PROVIDERS = [
  {
    provider: "Stripe",
    service: "Procesamiento de pagos",
    content:
      "Identificadores de pago, token de tarjeta, últimos 4 dígitos, marca, vencimiento e información de transacción necesaria para cobrar y gestionar contracargos.",
    purpose:
      "Procesar suscripciones, cargos recurrentes, validaciones de pago y aclaraciones relacionadas con cobros.",
  },
  {
    provider: "OpenAI",
    service: "Procesamiento de IA",
    content:
      "Prompts e instrucciones generadas por funciones del producto, incluyendo contexto de análisis, marcas, creators, campañas o entradas equivalentes que el usuario decida procesar.",
    purpose:
      "Generar análisis, recomendaciones y salidas asistidas por IA dentro de Kiizama.",
  },
  {
    provider: "Resend",
    service: "Correo transaccional",
    content:
      "Correo electrónico, nombre del usuario y metadatos mínimos necesarios para enviar mensajes operativos del servicio.",
    purpose:
      "Enviar correos de acceso, recuperación de contraseña, notificaciones operativas y otros mensajes transaccionales.",
  },
  {
    provider: "Sentry",
    service: "Monitoreo de errores",
    content:
      "Telemetría técnica, contexto de errores, eventos de falla y metadatos de diagnóstico necesarios para investigar incidentes del servicio.",
    purpose:
      "Detectar, registrar y corregir errores, degradaciones o incidentes de estabilidad en la plataforma.",
  },
] as const

export const Route = createFileRoute("/providers")({
  component: ProvidersPage,
})

function ProvidersPage() {
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" })
  }, [])

  return (
    <InfoPageShell maxW="7xl" useSymbolHomeButton>
      <Box layerStyle="infoCard" p={{ base: 6, md: 10 }}>
        <Stack gap={8}>
          <Stack gap={2}>
            <Text textStyle="eyebrow">Company</Text>
            <Heading size={{ base: "2xl", md: "3xl" }} textStyle="pageTitle">
              Proveedores de Kiizama
            </Heading>
          </Stack>

          <Stack as="section" gap={4}>
            <Text textStyle="pageBody">
              Esta página resume los proveedores externos integrados de forma
              directa en Kiizama a la fecha de última actualización. La tabla
              indica quién presta el servicio, qué tipo de contenido o datos
              puede intervenir al operar la plataforma y para qué se utiliza.
            </Text>
            <Text textStyle="pageBody">
              Esta información complementa nuestros{" "}
              <ChakraLink asChild className="legal-link">
                <RouterLink to="/terms-conditions">
                  Términos y Condiciones
                </RouterLink>
              </ChakraLink>{" "}
              y el{" "}
              <ChakraLink asChild className="legal-link">
                <RouterLink to="/privacy">Aviso de Privacidad</RouterLink>
              </ChakraLink>
              . Si incorporamos nuevos proveedores relevantes o cambia el
              alcance de los servicios actuales, actualizaremos esta página.
            </Text>
          </Stack>

          <Stack as="section" gap={4}>
            <Heading size="lg">Tabla de Proveedores</Heading>
            <Box overflowX="auto">
              <Table.Root size={{ base: "sm", md: "md" }} minW="980px">
                <Table.Header>
                  <Table.Row>
                    <Table.ColumnHeader>Proveedor</Table.ColumnHeader>
                    <Table.ColumnHeader>Servicio</Table.ColumnHeader>
                    <Table.ColumnHeader>
                      Contenido o datos involucrados
                    </Table.ColumnHeader>
                    <Table.ColumnHeader>Finalidad</Table.ColumnHeader>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  {PROVIDERS.map((provider) => (
                    <Table.Row key={provider.provider}>
                      <Table.Cell>{provider.provider}</Table.Cell>
                      <Table.Cell>{provider.service}</Table.Cell>
                      <Table.Cell>{provider.content}</Table.Cell>
                      <Table.Cell>{provider.purpose}</Table.Cell>
                    </Table.Row>
                  ))}
                </Table.Body>
              </Table.Root>
            </Box>
          </Stack>

          <Text color="ui.mutedText" fontSize="sm">
            Última actualización: 06/04/2026
          </Text>
        </Stack>
      </Box>
    </InfoPageShell>
  )
}
