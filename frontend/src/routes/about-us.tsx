import { Box, Heading, Stack, Text } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import InfoPageShell from "@/components/Common/InfoPageShell"

const ABOUT_US_TEMPLATE = `SOBRE KIIZAMA

Kiizama nace de una realidad bastante común: demasiada información, poco contexto y herramientas que no siempre ayudan a tomar mejores decisiones.

En medio de todo ese ruido, Kiizama llega para hacer algo más simple (y mucho más útil): transformar datos de redes sociales en análisis, reportes y estrategias que realmente ayudan a decidir mejor y con más criterio.

¿Qué es Kiizama? Kiizama es una plataforma de inteligencia para creators, marcas, agencias y equipos de comunicación. Combina datos de redes sociales, análisis asistido por IA y reportes descargables para facilitar decisiones mejor informadas. La propuesta no es quedarse en la superficie ni limitarse a mostrar métricas. Kiizama busca ayudar a entender mejor a los creators, organizar información útil, detectar oportunidades y convertir información operativa en dirección estratégica. En otras palabras: Kiizama convierte datos en criterio.`

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
