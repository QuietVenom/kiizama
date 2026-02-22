import { Box, Heading, Stack, Text } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import InfoPageShell from "@/components/Common/InfoPageShell"

const TERMS_TEMPLATE = `TÉRMINOS Y CONDICIONES DE USO Y SUSCRIPCIÓN (B2C – SaaS)

Versión: [v1.0]
Última actualización: [DD/MM/AAAA]

1) Identidad del Proveedor

[RAZÓN SOCIAL / NOMBRE COMERCIAL] (“Proveedor”, “nosotros”)
Domicilio: Ciudad de México, [domicilio completo]
RFC: [●]
Correo de contacto: [soporte@tudominio.com
]
Correo legal: [legal@tudominio.com
]

2) Aceptación de los Términos (contratación electrónica)

Al crear una cuenta, iniciar un Free Trial, contratar un plan, o usar el Servicio, aceptas estos Términos. La aceptación puede realizarse por medios electrónicos. (Referencia normativa general sobre contratación por medios electrónicos en México y conservación de evidencias; útil si decides robustecer “evidencia” de aceptación con sellado/constancia tipo NOM-151).

3) Definiciones

Servicio: Plataforma SaaS [NOMBRE DEL PRODUCTO] (web/app/API), documentación y funcionalidades.

Usuario/Consumidor: Persona física que usa el Servicio para fines no empresariales.

Cuenta: Perfil asociado a email para acceso.

Suscripción: Plan de pago Mensual o Anual con cobro recurrente.

Free Trial: Periodo de prueba sin costo por [X días], con o sin conversión automática (ver Cláusula 7).

Procesador de Pago: Tercero que procesa pagos (p. ej. Stripe, Conekta, MercadoPago) (ver Cláusula 8).

4) Objeto

Estos Términos regulan el acceso y uso del Servicio, y la contratación de Free Trial, Suscripción Mensual o Anual, en moneda MXN.

5) Requisitos de uso y cuenta

5.1 Debes tener capacidad legal para contratar.

5.2 Eres responsable de la confidencialidad de tu cuenta y de toda actividad realizada en ella.

5.3 Debes proporcionar información veraz y mantenerla actualizada.

6) Uso permitido y restricciones

No puedes:

usar el Servicio para fines ilícitos, fraude, spam o suplantación;

vulnerar seguridad, introducir malware, o intentar acceder a sistemas ajenos;

copiar, revender, “scrapear” masivamente, hacer ingeniería inversa o explotar el Servicio fuera del uso normal (salvo lo permitido por ley).

Podemos suspender o limitar acceso ante incumplimiento, abuso o riesgo de seguridad.

SUSCRIPCIONES, COBROS RECURRENTES Y CANCELACIÓN (B2C – MÉXICO)
7) Planes disponibles

Free Trial: [X días] con acceso a [alcance].

Mensual: cobro recurrente cada 30/31 días según fecha de alta.

Anual: cobro recurrente cada 12 meses.

Transparencia de cobro recurrente (obligatorio): Te informaremos de forma clara y accesible si tu contratación implica cobros automáticos recurrentes, su periodicidad, monto y fecha de cobro, y requerimos tu consentimiento expreso e informado.

8) Pagos, tarjeta y facturación

8.1 Moneda: MXN.
8.2 Tarjeta: Para Suscripción (y/o conversión de Trial) podrás registrar tarjeta mediante el Procesador de Pago.
8.3 No almacenamos tu tarjeta completa: Salvo que indiques lo contrario y sea técnicamente necesario, el Proveedor no almacena datos completos de tarjeta (PAN/CVV). Normalmente sólo conservamos identificadores como “token”, últimos 4 dígitos, marca y fecha de expiración, provistos por el Procesador.
8.4 Impuestos: Los precios [incluyen/no incluyen] IVA.
8.5 Comprobantes: Te enviaremos comprobantes/recibos al email. (Si después quieres ofrecer CFDI, agrega proceso y campos).

9) Renovación automática, aviso y cancelación sin penalización (LFPC 76 Bis – reforma 12-dic-2025)

9.1 Renovación automática: Si tu plan contempla renovación automática, te lo indicaremos durante el checkout.
9.2 Aviso previo mínimo: Si procede renovación automática del servicio, te notificaremos al menos con 5 días naturales de anticipación, permitiendo cancelación sin penalización.
9.3 Cancelación inmediata: Implementamos mecanismos para que puedas cancelar el servicio/suscripción/membresía de manera inmediata, sin trabas indebidas, conforme a la LFPC.
9.4 Cómo cancelar (mecanismo):

En la app/web: [Ruta exacta: Configuración → Suscripción → Cancelar]

O por correo: [cancelaciones@tudominio.com
] (te responderemos con confirmación).
9.5 Efecto de la cancelación: La cancelación evita cobros futuros. El acceso permanecerá activo hasta el fin del periodo pagado [sí/no] (elige uno y mantén consistencia).

10) Free Trial: reglas de conversión y cobro

Define UNA de estas 2 modalidades (recomendación: A es más “safe” en B2C):

A) Trial sin conversión automática (recomendado):

El Trial termina y no se cobra nada salvo que tú actives un plan y confirmes pago.

B) Trial con conversión automática (si la usarás):

Antes de iniciar Trial te diremos claramente: precio, periodicidad, fecha exacta del primer cobro y que habrá cobro recurrente.

Requerimos tu consentimiento expreso e informado.

Te avisaremos al menos 5 días naturales antes de la renovación/cobro y podrás cancelar sin penalización.

11) Reembolsos y contracargos (B2C)

11.1 Política general:

Mensual: [No hay reembolsos / Reembolso parcial dentro de X días / caso por caso].

Anual: [No hay reembolsos / prorrateo / reembolso dentro de X días].
11.2 Cobros indebidos: Si consideras que hubo un cobro erróneo, contáctanos a [soporte] dentro de [15] días.
11.3 Contracargos: Si inicias un contracargo sin contactarnos primero, podremos suspender la cuenta mientras se resuelve.

Tip B2C: la política debe ser súper clara y visible en checkout para evitar conflictos con consumidor.

PRIVACIDAD Y DATOS PERSONALES (México)
12) Datos que recabamos y finalidades

Recabamos: email, nombre completo, y datos relacionados con el pago a través del Procesador (tokens/identificadores).
Tu información se trata conforme a nuestro Aviso de Privacidad: [URL Aviso de Privacidad]. La LFPDPPP establece obligaciones del responsable y el marco de tratamiento de datos personales en posesión de particulares.

13) Derechos ARCO y contacto

Puedes ejercer derechos ARCO (Acceso, Rectificación, Cancelación, Oposición) mediante: [privacidad@tudominio.com
] y el procedimiento del Aviso de Privacidad.

14) Proveedores y transferencias

Podemos usar proveedores (hosting, analítica, email, pagos) que traten datos por cuenta nuestra. Se listan en [URL lista de subencargados/proveedores].

PROPIEDAD INTELECTUAL, GARANTÍAS Y RESPONSABILIDAD
15) Propiedad intelectual

El Servicio, software, marca, interfaz y documentación son del Proveedor o licenciantes.
Te damos una licencia limitada, personal, no exclusiva y no transferible para usar el Servicio mientras tu cuenta/suscripción esté activa.

16) Disponibilidad y soporte

16.1 Soporte: [email/chat], horario [●].
16.2 Mantenimiento: puede haber interrupciones programadas; procuraremos avisar.

17) Limitación de responsabilidad

En la medida permitida por ley, el Proveedor no responde por daños indirectos (lucro cesante, pérdida de datos, etc.).
La responsabilidad total del Proveedor se limita a [monto pagado por el Usuario en los últimos 3/6/12 meses].

Ojo: en B2C, evita cláusulas abusivas o desproporcionadas; tu abogadx puede ajustar para que sea defendible frente a PROFECO.

18) Terminación

Podemos suspender/terminar si incumples estos Términos, o por motivos de seguridad, fraude o requerimiento de autoridad.
Al terminar, podrías perder acceso; definimos un periodo de exportación de datos si aplica: [X días].

DISPOSICIONES GENERALES
19) Modificaciones a los Términos

Podremos modificar estos Términos por mejoras, cambios legales o de negocio. Te notificaremos en la app o por email. El uso posterior implica aceptación.

20) Ley aplicable y jurisdicción

Estos Términos se rigen por las leyes de los Estados Unidos Mexicanos. Para controversias, las partes se someten a tribunales competentes de Ciudad de México, salvo reglas imperativas de protección al consumidor.

21) Contacto y quejas

Soporte: [soporte@tudominio.com
]
Cancelaciones: [cancelaciones@tudominio.com
]
Privacidad: [privacidad@tudominio.com
]`

export const Route = createFileRoute("/terms-conditions")({
  component: TermsConditionsPage,
})

function TermsConditionsPage() {
  return (
    <InfoPageShell>
      <Box
        bg="white"
        borderWidth="1px"
        borderColor="gray.100"
        rounded="3xl"
        p={{ base: 6, md: 10 }}
        boxShadow="0 16px 34px rgba(15, 23, 42, 0.06)"
      >
        <Stack gap={4}>
          <Text
            color="orange.500"
            textTransform="uppercase"
            fontWeight="bold"
            letterSpacing="0.12em"
            fontSize="xs"
          >
            Company
          </Text>
          <Heading
            size={{ base: "2xl", md: "3xl" }}
            color="gray.900"
            letterSpacing="-0.02em"
            fontFamily="'Plus Jakarta Sans', 'Avenir Next', 'Segoe UI', sans-serif"
          >
            Terms & Conditions
          </Heading>
          <Text color="gray.700" whiteSpace="pre-line" lineHeight="1.8">
            {TERMS_TEMPLATE}
          </Text>
        </Stack>
      </Box>
    </InfoPageShell>
  )
}
