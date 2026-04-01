import { Box, Link as ChakraLink, Heading, Stack, Text } from "@chakra-ui/react"
import { createFileRoute, Link as RouterLink } from "@tanstack/react-router"
import { useEffect } from "react"
import InfoPageShell from "@/components/Common/InfoPageShell"

const TERMS_TEMPLATE = `TÉRMINOS Y CONDICIONES DE USO Y SUSCRIPCIÓN (B2C – SaaS)

Versión: v1.0
Última actualización: 06/04/2026

1) Identidad del Proveedor

Izcoatl Ávila Marcos (“Proveedor”, “nosotros”)
Domicilio: Santa Fe, CDMX.
RFC: AIMI91041597A
Correo de contacto: admin@kiizama.com
Correo legal: NA

2) Aceptación de los Términos (contratación electrónica)

Al crear una cuenta, iniciar un Free Trial, contratar un plan o usar el Servicio, aceptas estos Términos. La aceptación podrá realizarse por medios electrónicos y tendrá la misma validez que una firma autógrafa en la medida permitida por la ley aplicable.

3) Definiciones

Servicio: Plataforma SaaS Kiizama (web/app/API), documentación y funcionalidades.

Usuario/Consumidor: Persona física que usa el Servicio para fines no empresariales.

Cuenta: Perfil asociado a email para acceso.

Suscripción: Plan de pago mensual o anual con cobro recurrente.

Free Trial: Periodo de prueba sin costo por 7 días, sin conversión automática.

Procesador de Pago: Stripe, a través de tarjetas de crédito o débito.

4) Objeto

Estos Términos regulan el acceso y uso del Servicio, y la contratación de Free Trial, Suscripción Mensual o Anual, en moneda MXN.

5) Requisitos de uso y cuenta

5.1 Debes tener capacidad legal para contratar.

5.2 Eres responsable de la confidencialidad de tu cuenta y de toda actividad realizada en ella.

5.3 Debes proporcionar información veraz y mantenerla actualizada.

6) Uso permitido y restricciones

No puedes:

- usar el Servicio para fines ilícitos, fraude, spam o suplantación;
- vulnerar seguridad, introducir malware o intentar acceder a sistemas ajenos;
- copiar, revender, “scrapear” masivamente, hacer ingeniería inversa o explotar el Servicio fuera del uso normal, salvo lo permitido por ley.

Podemos suspender o limitar acceso ante incumplimiento, abuso o riesgo de seguridad.

SUSCRIPCIONES, COBROS RECURRENTES Y CANCELACIÓN (B2C – MÉXICO)
7) Planes disponibles

Free Trial: 7 días con acceso a las funcionalidades base de Kiizama, excluyendo integraciones avanzadas, exportaciones masivas y funciones empresariales o premium.

Mensual: cobro recurrente cada 30/31 días según fecha de alta.

Anual: cobro recurrente cada 12 meses.

Te informaremos de forma clara y accesible si tu contratación implica cobros automáticos recurrentes, su periodicidad, monto y fecha de cobro, y requeriremos tu consentimiento expreso e informado.

8) Pagos, tarjeta y facturación

8.1 Moneda: MXN.

8.2 Tarjeta: Para Suscripción (y/o conversión de Trial) podrás registrar tarjeta mediante el Procesador de Pago.

8.3 No almacenamos tu tarjeta completa: Salvo que indiques lo contrario y sea técnicamente necesario, el Proveedor no almacena datos completos de tarjeta (PAN/CVV). Normalmente sólo conservamos identificadores como “token”, últimos 4 dígitos, marca y fecha de expiración, provistos por el Procesador.

8.4 Impuestos: Los precios incluyen IVA.

8.5 Comprobantes: Te enviaremos comprobantes o recibos al correo electrónico registrado en tu cuenta.

9) Renovación automática, aviso y cancelación sin penalización (LFPC 76 Bis – reforma 12-dic-2025)

9.1 Renovación automática: Si tu plan contempla renovación automática, te lo indicaremos durante el checkout.

9.2 Aviso previo mínimo: Si procede renovación automática del servicio, te notificaremos al menos con 5 días naturales de anticipación, permitiendo cancelación sin penalización.

9.3 Cancelación inmediata: Implementamos mecanismos para que puedas cancelar el servicio/suscripción/membresía de manera inmediata, sin trabas indebidas, conforme a la LFPC.

9.4 Cómo cancelar (mecanismo):

En la app/web: http://app.kiizama.com/settings

O por correo: admin@kiizama.com.

9.5 Efecto de la cancelación: La cancelación evita cobros futuros. El acceso no permanecerá activo hasta el fin del periodo pagado.

10) Free Trial: reglas de conversión y cobro

Trial sin conversión automática:

El Trial termina y no se cobra nada salvo que tú actives un plan y confirmes pago.

11) Reembolsos y contracargos (B2C)

11.1 Política general:

Mensual: Reembolso dentro de los primeros 7 días.

Anual: Reembolso dentro de los primeros 7 días.

11.2 Cobros indebidos: Si consideras que hubo un cobro erróneo, contáctanos a admin@kiizama.com dentro de 15 días.

11.3 Contracargos: Si inicias un contracargo sin contactarnos primero, podremos suspender la cuenta mientras se resuelve.

PRIVACIDAD Y DATOS PERSONALES (México)
12) Datos que recabamos y finalidades

Recabamos: email, nombre completo, y datos relacionados con el pago a través del Procesador (tokens/identificadores).

Tu información se trata conforme a nuestro Aviso de Privacidad: http://www.kiizama.com/privacy. La LFPDPPP establece obligaciones del responsable y el marco de tratamiento de datos personales en posesión de particulares.

13) Derechos ARCO y contacto

Puedes ejercer derechos ARCO (Acceso, Rectificación, Cancelación, Oposición) mediante: admin@kiizama.com y el procedimiento del Aviso de Privacidad.

14) Proveedores y transferencias

Podemos usar proveedores (hosting, analítica, email, pagos) que traten datos por cuenta nuestra. Se listan en __PROVIDERS_LINK__.

PROPIEDAD INTELECTUAL, GARANTÍAS Y RESPONSABILIDAD
15) Propiedad intelectual

El Servicio, software, marca, interfaz y documentación son del Proveedor o licenciantes.

Te damos una licencia limitada, personal, no exclusiva y no transferible para usar el Servicio mientras tu cuenta/suscripción esté activa.

16) Disponibilidad y soporte

16.1 Soporte: admin@kiizama.com, horario de 09:00 a 18:00 hrs (UTC-06:00, hora de Ciudad de México).

16.2 Mantenimiento: puede haber interrupciones programadas; procuraremos avisar.

17) Limitación de responsabilidad

En la medida permitida por ley, el Proveedor no responde por daños indirectos (lucro cesante, pérdida de datos, etc.).

La responsabilidad total del Proveedor se limita al monto efectivamente pagado por el Usuario por el Servicio en los últimos 12 meses previos al hecho que dé lugar a la reclamación.

18) Terminación

Podemos suspender/terminar si incumples estos Términos, o por motivos de seguridad, fraude o requerimiento de autoridad.

Al terminar, podremos conservar, bloquear o eliminar los datos personales asociados conforme a nuestro Aviso de Privacidad y a las obligaciones legales aplicables.

DISPOSICIONES GENERALES
19) Modificaciones a los Términos

Podremos modificar estos Términos por mejoras, cambios legales o de negocio. Te notificaremos en la app o por email. El uso posterior implica aceptación.

20) Ley aplicable y jurisdicción

Estos Términos se rigen por las leyes de los Estados Unidos Mexicanos. Para controversias, las partes se someten a tribunales competentes de Ciudad de México, salvo reglas imperativas de protección al consumidor.

21) Contacto y quejas

Soporte: admin@kiizama.com
Cancelaciones: admin@kiizama.com
Privacidad: admin@kiizama.com`

export const Route = createFileRoute("/terms-conditions")({
  component: TermsConditionsPage,
})

function TermsConditionsPage() {
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" })
  }, [])

  const [termsBeforeProvidersLink, termsAfterProvidersLink] =
    TERMS_TEMPLATE.split("__PROVIDERS_LINK__")

  return (
    <InfoPageShell useSymbolHomeButton>
      <Box layerStyle="infoCard" p={{ base: 6, md: 10 }}>
        <Stack gap={4}>
          <Text textStyle="eyebrow">Company</Text>
          <Heading size={{ base: "2xl", md: "3xl" }} textStyle="pageTitle">
            Términos y Condiciones
          </Heading>
          <Text textStyle="pageBody" whiteSpace="pre-line">
            {termsBeforeProvidersLink}
            <ChakraLink asChild className="legal-link">
              <RouterLink to="/providers">/providers</RouterLink>
            </ChakraLink>
            {termsAfterProvidersLink}
          </Text>
        </Stack>
      </Box>
    </InfoPageShell>
  )
}
