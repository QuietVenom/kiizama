import { Box, Heading, Stack, Text } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import InfoPageShell from "@/components/Common/InfoPageShell"

const ABOUT_US_TEMPLATE = `SOBRE KIIZAMA

Kiizama nace en un contexto muy concreto: creators, marcas, agencias y equipos de comunicación trabajan todos los días con mucha información dispersa, poco contexto accionable y herramientas que no siempre ayudan a decidir mejor.

Frente a ese problema, Kiizama se construye como una plataforma de inteligencia que transforma datos de redes sociales en análisis, reportes y estrategias útiles para tomar decisiones con más criterio.

¿Qué es Kiizama?

Kiizama es una plataforma de inteligencia para creators, marcas, agencias y equipos de comunicación. Combina datos de redes sociales, análisis asistido por IA y reportes descargables para facilitar decisiones mejor informadas.

La propuesta no es quedarse en la superficie ni limitarse a mostrar métricas. Kiizama busca ayudar a entender mejor a los creators, organizar información útil, detectar oportunidades y convertir información operativa en dirección estratégica.

En otras palabras: Kiizama convierte datos en criterio.`

export const Route = createFileRoute("/about-us")({
  component: AboutUsPage,
})

function AboutUsPage() {
  return (
    <InfoPageShell>
      <Box layerStyle="infoCard" p={{ base: 6, md: 10 }}>
        <Stack gap={4}>
          <Text textStyle="eyebrow">Company</Text>
          <Heading size={{ base: "2xl", md: "3xl" }} textStyle="pageTitle">
            Sobre Nosotros
          </Heading>
          <Text textStyle="pageBody" whiteSpace="pre-line">
            {ABOUT_US_TEMPLATE}
          </Text>
        </Stack>
      </Box>
    </InfoPageShell>
  )
}
