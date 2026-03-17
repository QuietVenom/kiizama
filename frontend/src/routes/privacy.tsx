import { Box, Heading, Stack, Text } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import { useEffect } from "react"
import InfoPageShell from "@/components/Common/InfoPageShell"

const PRIVACY_TEMPLATE = `AVISO DE PRIVACIDAD INTEGRAL (LFPDPPP) — SaaS B2C

Versión: [v1.0]
Última actualización: [DD/MM/AAAA]

1) Identidad y domicilio del responsable

[RAZÓN SOCIAL / NOMBRE COMERCIAL] (en lo sucesivo, el “Responsable”) es quien decide sobre el tratamiento de sus datos personales.
Domicilio: Ciudad de México, [calle, número, colonia, alcaldía, C.P.], México.
Contacto de privacidad: [privacidad@tudominio.com
]

Este apartado es parte del contenido mínimo exigido para el aviso integral.

2) Datos personales que recabamos

Para prestar el servicio de [NOMBRE DEL PRODUCTO] (SaaS), podemos recabar:

a) Datos de identificación y contacto

Nombre completo

Correo electrónico

b) Datos de pago

Datos necesarios para procesar pagos con tarjeta a través de un tercero procesador de pagos (por ejemplo: token de pago, identificadores de transacción, últimos 4 dígitos, marca y fecha de expiración).
Nota: El Responsable no almacena el número completo de tarjeta ni el CVV; el procesamiento se realiza por el proveedor de pagos.

3) Finalidades del tratamiento

Sus datos personales serán utilizados para las siguientes finalidades:

Finalidades primarias (necesarias para el servicio)

Crear y administrar su cuenta en la plataforma.

Identificarlo y autenticarlo para permitir el acceso.

Prestar el servicio contratado, habilitar funcionalidades y administrar su suscripción (Free Trial / Mensual / Anual).

Gestionar cobros, pagos, facturación/recibos, prevención de fraude y devoluciones/contracargos (cuando aplique).

Enviar comunicaciones operativas: confirmaciones, avisos de cambios importantes al servicio, seguridad y soporte.

Atender solicitudes, dudas, aclaraciones y soporte técnico.

Finalidades secundarias (no necesarias)

Envío de promociones, novedades, mercadotecnia o prospección comercial.

Analítica para mejorar experiencia, métricas de uso y calidad del servicio.

Si no desea que sus datos se traten para las finalidades secundarias, puede manifestarlo en cualquier momento enviando un correo a: [privacidad@tudominio.com
] con el asunto “Negativa finalidades secundarias”.

La LFPDPPP y los Lineamientos exigen informar finalidades y distinguir (en la práctica) las secundarias para permitir oposición.

4) Opciones y medios para limitar el uso o divulgación

Usted puede:

Solicitar la baja de comunicaciones comerciales (cuando existan) mediante el enlace de “unsubscribe” o escribiendo a [privacidad@tudominio.com
].

Ajustar preferencias dentro de la cuenta, si está habilitado.

5) Medios para ejercer derechos ARCO

Usted tiene derecho a Acceder, Rectificar, Cancelar u Oponerse (derechos ARCO) al tratamiento de sus datos personales, conforme a la LFPDPPP.

Procedimiento

Para ejercer sus derechos ARCO, envíe una solicitud al correo: [privacidad@tudominio.com
] con:

Nombre del titular y medio para comunicar la respuesta (correo).

Copia/imagen de identificación oficial (para acreditar identidad).

Descripción clara de los datos respecto de los que busca ejercer el derecho.

En caso de rectificación, indicar la corrección y, si es posible, documentación soporte.

Plazos de respuesta: [20] días hábiles para determinar procedencia y [15] días hábiles adicionales para hacer efectiva la solicitud (estos plazos suelen usarse como práctica estándar alineada al marco LFPDPPP).

6) Transferencias de datos personales

Sus datos personales podrán ser transferidos sin requerir su consentimiento adicional cuando sea necesario para cumplir las finalidades primarias, por ejemplo:

Procesadores de pago para gestionar cargos y cobros.

Proveedores de infraestructura tecnológica (hosting, almacenamiento, correo transaccional, monitoreo) en calidad de encargados.

En estos casos, el Responsable procurará que dichos terceros asuman obligaciones de confidencialidad y medidas de seguridad razonables.

Debes informar transferencias y, en general, el “deber de informar” se articula vía aviso.

7) Uso de cookies y tecnologías de rastreo (si aplica)

Podemos utilizar cookies, web beacons y tecnologías similares para: recordar sesión, mejorar experiencia, seguridad, analítica y publicidad (si aplica).
Puede deshabilitar cookies desde la configuración de su navegador; algunas funciones podrían verse afectadas.

8) Medidas de seguridad

El Responsable implementa medidas de seguridad administrativas, técnicas y físicas razonables para proteger sus datos contra daño, pérdida, alteración, destrucción o uso, acceso o tratamiento no autorizado.

El Reglamento pide que el aviso sea claro y sencillo y se difunda por medios adecuados; además, prácticas de seguridad deben comunicarse de forma razonable.

9) Cambios al Aviso de Privacidad

El Responsable podrá modificar o actualizar este Aviso de Privacidad por cambios legales, mejoras del servicio o políticas internas.
Las actualizaciones se publicarán en: [URL del aviso] y, cuando sea relevante, se notificarán por correo o dentro de la plataforma.

10) Consentimiento

Al usar el Servicio y/o proporcionar sus datos por medios electrónicos, usted reconoce haber leído este Aviso de Privacidad y, cuando sea aplicable, otorga su consentimiento para el tratamiento conforme a lo aquí descrito.

La obligación del responsable de poner a disposición el aviso y cumplir el principio de información está prevista en el marco LFPDPPP/Lineamientos.`

export const Route = createFileRoute("/privacy")({
  component: PrivacyPage,
})

function PrivacyPage() {
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" })
  }, [])

  return (
    <InfoPageShell useSymbolHomeButton>
      <Box layerStyle="infoCard" p={{ base: 6, md: 10 }}>
        <Stack gap={4}>
          <Text textStyle="eyebrow">Company</Text>
          <Heading size={{ base: "2xl", md: "3xl" }} textStyle="pageTitle">
            Privacy
          </Heading>
          <Text textStyle="pageBody" whiteSpace="pre-line">
            {PRIVACY_TEMPLATE}
          </Text>
        </Stack>
      </Box>
    </InfoPageShell>
  )
}
