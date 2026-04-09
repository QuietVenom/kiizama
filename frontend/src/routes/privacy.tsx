import { Box, Link as ChakraLink, Heading, Stack, Text } from "@chakra-ui/react"
import { createFileRoute, Link as RouterLink } from "@tanstack/react-router"
import { useEffect } from "react"
import InfoPageShell from "@/components/Common/InfoPageShell"

const PRIVACY_TEMPLATE = `AVISO DE PRIVACIDAD INTEGRAL (LFPDPPP) — SaaS B2C

Versión: v1.0
Última actualización: 06/04/2026

1) Identidad y domicilio del responsable

Izcoatl Ávila Marcos (el “Responsable”) es quien decide sobre el tratamiento de sus datos personales.
Domicilio: Santa Fe, CDMX, México.
RFC: AIMI91041597A
Contacto de privacidad: admin@kiizama.com

2) Datos personales que recabamos

Para prestar el servicio de Kiizama, recabamos los siguientes datos personales:

a) Datos de identificación y contacto

Nombre completo

Correo electrónico

b) Datos de pago

Datos necesarios para procesar pagos con tarjeta a través de un tercero procesador de pagos, incluyendo token de pago, identificadores de transacción, últimos 4 dígitos, marca y fecha de expiración.

El Responsable no almacena el número completo de tarjeta ni el CVV; el procesamiento se realiza por Stripe.

3) Finalidades del tratamiento

Sus datos personales serán utilizados para las siguientes finalidades:

Finalidades primarias (necesarias para el servicio)

- Crear y administrar su cuenta en la plataforma.
- Identificarlo y autenticarlo para permitir el acceso.
- Prestar el servicio contratado, habilitar funcionalidades y administrar su suscripción (Free Trial / Mensual / Anual).
- Gestionar cobros, pagos, facturación o recibos, prevención de fraude y devoluciones o contracargos, cuando corresponda.
- Enviar comunicaciones operativas, incluyendo confirmaciones, avisos de cambios importantes al servicio, seguridad y soporte.
- Atender solicitudes, dudas, aclaraciones y soporte técnico.

Finalidades secundarias (no necesarias)

- Envío de promociones, novedades, mercadotecnia o prospección comercial.
- Analítica para mejorar la experiencia, métricas de uso y calidad del servicio.

Si no desea que sus datos se traten para las finalidades secundarias, puede manifestarlo en cualquier momento enviando un correo a admin@kiizama.com con el asunto “Negativa finalidades secundarias”.

4) Opciones y medios para limitar el uso o divulgación

Usted puede:

- Solicitar la baja de comunicaciones comerciales, cuando existan, mediante el enlace de “unsubscribe” o escribiendo a admin@kiizama.com.
- Ajustar preferencias dentro de la cuenta, si está habilitado.

5) Medios para ejercer derechos ARCO

Usted tiene derecho a Acceder, Rectificar, Cancelar u Oponerse (derechos ARCO) al tratamiento de sus datos personales, conforme a la LFPDPPP.

Procedimiento

Para ejercer sus derechos ARCO, envíe una solicitud al correo admin@kiizama.com con:

- Nombre del titular y medio para comunicar la respuesta.
- Copia o imagen de identificación oficial para acreditar identidad.
- Descripción clara de los datos respecto de los que busca ejercer el derecho.
- En caso de rectificación, la corrección solicitada y, de ser posible, documentación soporte.

Plazos de respuesta: 20 días hábiles para determinar la procedencia y 15 días hábiles adicionales para hacer efectiva la solicitud, en caso de que resulte procedente.

6) Transferencias de datos personales

Sus datos personales podrán ser transferidos sin requerir su consentimiento adicional cuando sea necesario para cumplir las finalidades primarias, incluyendo los siguientes supuestos:

- Procesadores de pago para gestionar cargos y cobros.
- Proveedores de infraestructura tecnológica, correo transaccional, monitoreo, analítica y procesamiento operativo, en calidad de encargados.

En estos casos, el Responsable exigirá a dichos terceros obligaciones de confidencialidad y medidas de seguridad acordes con la naturaleza de los datos tratados. La lista de proveedores relevantes puede consultarse en __PROVIDERS_LINK__.

7) Uso de cookies y tecnologías de rastreo

Podemos utilizar cookies, web beacons y tecnologías similares para recordar sesión, mejorar la experiencia, reforzar la seguridad, obtener analítica y, en su caso, soportar actividades publicitarias.

Puede deshabilitar cookies desde la configuración de su navegador; algunas funciones podrían verse afectadas.

Para más información, consulte nuestra Política de Cookies en __COOKIE_NOTICE_LINK__ y las tablas informativas en __COOKIE_TABLES_LINK__.

8) Medidas de seguridad

El Responsable implementa medidas de seguridad administrativas, técnicas y físicas razonables para proteger sus datos contra daño, pérdida, alteración, destrucción o uso, acceso o tratamiento no autorizado.

9) Cambios al Aviso de Privacidad

El Responsable podrá modificar o actualizar este Aviso de Privacidad por cambios legales, mejoras del servicio o políticas internas.

Las actualizaciones se publicarán en __PRIVACY_LINK__ y, en caso de cambios relevantes, se notificarán por correo o dentro de la plataforma.

10) Consentimiento

Al usar el Servicio y/o proporcionar sus datos por medios electrónicos, usted reconoce haber leído este Aviso de Privacidad y, cuando resulte aplicable, consiente el tratamiento de sus datos conforme a lo aquí descrito.
`

export const Route = createFileRoute("/privacy")({
  component: PrivacyPage,
})

function PrivacyPage() {
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" })
  }, [])

  const [providersBeforeLink, providersAfterLink] =
    PRIVACY_TEMPLATE.split("__PROVIDERS_LINK__")
  const [cookiesBeforeNoticeLink, cookiesAfterNoticeLink] =
    providersAfterLink.split("__COOKIE_NOTICE_LINK__")
  const [cookiesBeforeTablesLink, cookiesAfterTablesLink] =
    cookiesAfterNoticeLink.split("__COOKIE_TABLES_LINK__")
  const [privacyBeforeLink, privacyAfterLink] =
    cookiesAfterTablesLink.split("__PRIVACY_LINK__")

  return (
    <InfoPageShell useSymbolHomeButton>
      <Box layerStyle="infoCard" p={{ base: 6, md: 10 }}>
        <Stack gap={4}>
          <Text textStyle="eyebrow">Company</Text>
          <Heading size={{ base: "2xl", md: "3xl" }} textStyle="pageTitle">
            Aviso de Privacidad
          </Heading>
          <Text textStyle="pageBody" whiteSpace="pre-line">
            {providersBeforeLink}
            <ChakraLink asChild className="legal-link">
              <RouterLink to="/providers">/providers</RouterLink>
            </ChakraLink>
            {cookiesBeforeNoticeLink}
            <ChakraLink asChild className="legal-link">
              <RouterLink to="/cookie-notice">/cookie-notice</RouterLink>
            </ChakraLink>
            {cookiesBeforeTablesLink}
            <ChakraLink asChild className="legal-link">
              <RouterLink to="/cookie-tables">/cookie-tables</RouterLink>
            </ChakraLink>
            {privacyBeforeLink}
            <ChakraLink asChild className="legal-link">
              <RouterLink to="/privacy">/privacy</RouterLink>
            </ChakraLink>
            {privacyAfterLink}
          </Text>
        </Stack>
      </Box>
    </InfoPageShell>
  )
}
