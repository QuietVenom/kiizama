import { Box, Heading, Stack, Text } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import { useEffect } from "react"
import InfoPageShell from "@/components/Common/InfoPageShell"

const SECURITY_TEMPLATE = `SEGURIDAD

Última actualización: 06/04/2026

En Kiizama aplicamos medidas técnicas y operativas orientadas a proteger el acceso a la plataforma, reducir abuso de servicios y responder a incidentes de forma razonable. Esta página resume, de forma general, algunos de los controles actualmente implementados.

1) Acceso y autenticación

- El acceso a la aplicación requiere autenticación.
- Las contraseñas no se almacenan en texto plano.
- El sistema utiliza tokens de acceso para sesiones autenticadas.
- Existe flujo de recuperación y restablecimiento de contraseña.

2) Protección operativa

- Aplicamos controles de rate limiting en rutas sensibles, incluyendo inicio de sesión y recuperación de contraseña.
- Restringimos orígenes permitidos en la API mediante configuración de CORS.
- Mantenemos validaciones de configuración para evitar secretos inseguros en despliegues.

3) Monitoreo y continuidad

- Utilizamos monitoreo de errores en entornos aplicables para detectar fallas e incidentes operativos.
- Verificamos disponibilidad de dependencias críticas como base de datos y Redis durante el arranque y en verificaciones de salud.
- Algunos servicios pueden operar en modo degradado si una dependencia secundaria no está disponible.

4) Pagos

- El procesamiento de pagos se realiza mediante Stripe.
- Kiizama no almacena el número completo de tarjeta ni el CVV.

5) Alcance

Ninguna medida de seguridad ofrece protección absoluta. Revisamos y ajustamos controles conforme evoluciona el producto, la infraestructura y el nivel de riesgo.

Si desea reportar una incidencia de seguridad o una vulnerabilidad relacionada con Kiizama, puede escribir a admin@kiizama.com.`

export const Route = createFileRoute("/security")({
  component: SecurityPage,
})

function SecurityPage() {
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" })
  }, [])

  return (
    <InfoPageShell useSymbolHomeButton>
      <Box layerStyle="infoCard" p={{ base: 6, md: 10 }}>
        <Stack gap={4}>
          <Text textStyle="eyebrow">Company</Text>
          <Heading size={{ base: "2xl", md: "3xl" }} textStyle="pageTitle">
            Seguridad
          </Heading>
          <Text textStyle="pageBody" whiteSpace="pre-line">
            {SECURITY_TEMPLATE}
          </Text>
        </Stack>
      </Box>
    </InfoPageShell>
  )
}
