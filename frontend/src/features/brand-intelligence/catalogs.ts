export const BRAND_GOALS_TYPE_OPTIONS = [
  "Trust & Credibility Acceleration",
  "Repositioning",
  "Crisis",
] as const

export const CREATOR_GOAL_TYPE_OPTIONS = [
  "Community Trust",
  "Resilience",
  "Pivot",
] as const

export const AUDIENCE_OPTIONS = [
  "Gen Z",
  "Zillennials",
  "Millennials",
  "Gen X",
  "Boomers",
] as const

export const TIMEFRAME_OPTIONS = ["3 months", "6 months", "12 months"] as const

export const CAMPAIGN_TYPE_OPTIONS = [
  {
    name: "all_nano_seeding_ugc_flood",
    title: 'All Nano "Seeding / UGC flood"',
    value:
      "Mix: 20-200 nanos (1k-10k). Objetivo: UGC, reviews reales, volumen de menciones, prueba social y contenido para repost. Ideal para: lanzamientos, ecomm, CPG, restaurantes y apps en early stage. Clave: pago hibrido (producto/experiencia + comision) y un brief muy simple.",
  },
  {
    name: "all_micro_performance_community_trust",
    title: 'All Micro "Performance + community trust"',
    value:
      "Mix: 10-80 micros (10k-100k). Objetivo: conversiones, clicks, registros y ventas con confianza por cercania. Ideal para: performance marketing, fintech, cursos, beauty y DTC. Clave: codigos/UTMs + bonus por resultados.",
  },
  {
    name: "micro_city_blitz",
    title: 'Micro "City Blitz" (por plazas)',
    value:
      "Mix: 5-20 micros por ciudad (CDMX/GDL/MTY/BAJIO/etc.). Objetivo: awareness local + trafico a tienda/evento. Ideal para: retail, aperturas, eventos y food delivery. Clave: ventanas cortas (timeframe) y mensajes/local hooks.",
  },
  {
    name: "all_mid_tier_reach_eficiente",
    title: 'All Mid-tier "Reach eficiente"',
    value:
      "Mix: 5-20 mids (100k-500k). Objetivo: awareness fuerte sin pagar macro/mega y buen CPM real. Ideal para: marcas con presupuesto medio que necesitan escala. Clave: creatividad alta y limitar exclusividad/rights.",
  },
  {
    name: "macro_plus_micro_swarm_hero_halo",
    title: '"1-3 Macro + Micro swarm" (Hero + halo)',
    value:
      "Mix: 1-3 macros (500k-1M) + 20-100 micros. Objetivo: macro abre conversacion, micro la sostiene y convierte. Ideal para: lanzamientos grandes y campanas de temporada. Clave: macro con mensaje core y micros con angulos (beneficios, reviews, tutorial).",
  },
  {
    name: "mega_plus_mid_support",
    title: '"Mega + Mid support" (Top-of-funnel + depth)',
    value:
      "Mix: 1 mega (1M+) + 10-30 mids. Objetivo: alcance masivo + credibilidad + repeticion. Ideal para: awareness nacional, branding y PR moments. Clave: mids con contenido educativo/demostracion (no solo hype).",
  },
  {
    name: "mid_plus_micro_always_on",
    title: '"2-5 Mid + Micro always-on"',
    value:
      "Mix: 2-5 mids (como anclas) + 10-30 micros mensuales. Objetivo: presencia constante (always-on) y construccion de marca. Ideal para: categorias competitivas (beauty, fitness, fintech). Clave: contrato 3-6 meses y rotacion de micros para evitar fatiga.",
  },
  {
    name: "celebrity_plus_community_creators",
    title: '"Celebrity + Community creators" (PR impact + authenticity)',
    value:
      "Mix: 1 celebrity + 20-60 nanos/micros. Objetivo: PR/earned media + legitimidad de la gente. Ideal para: reposicionamiento, causas y campanas culturales. Clave: celebrity para titulares; comunidad para conversacion organica.",
  },
  {
    name: "vertical_experts_authority",
    title: '"Vertical experts" (Autoridad)',
    value:
      "Mix: 5-15 creadores expertos (micro/mid). Objetivo: consideracion, confianza y educacion (finanzas, salud, tech). Ideal para: fintech, B2B, educacion y health/wellness. Clave: formatos largos (YouTube/podcast) + piezas cortas recortadas.",
  },
  {
    name: "ugc_creators",
    title: '"UGC creators (no importa el follower count)"',
    value:
      "Mix: 10-50 UGC creators (a veces <10k). Objetivo: producir anuncios/contenido para paid sin pagar creator rates. Ideal para: performance ads (Meta/TikTok). Clave: pagar por produccion + derechos de uso; no por reach.",
  },
  {
    name: "event_amplification",
    title: '"Event amplification"',
    value:
      "Mix: 1-2 macros o mega + 10-30 micros/nanos en el evento. Objetivo: cobertura en vivo, FOMO, asistencia y PR social. Ideal para: lanzamientos, pop-ups, festivales y press trips. Clave: plan de momentos (arribo, highlight, CTA) y entregables claros.",
  },
  {
    name: "challenge_trend_wave",
    title: '"Challenge / Trend wave"',
    value:
      "Mix: 1 mid/macro que arranque + 30-150 micros/nanos que lo repliquen. Objetivo: viralidad y repeticion del concepto. Ideal para: TikTok, musica y consumo masivo. Clave: mecanica super simple + incentivo (premios, features).",
  },
  {
    name: "creator_squad_ambassadors",
    title: '"Creator squad" (embajadores)',
    value:
      "Mix: 6-20 creadores (micro/mid) por 6-12 meses. Objetivo: consistencia + asociacion de marca. Ideal para: lifestyle, sports, beauty y fintech friendly. Clave: contrato con exclusividad razonable + perks + contenido mensual.",
  },
  {
    name: "retargeting_booster_paid_whitelisting",
    title: '"Retargeting booster" (paid + whitelisting)',
    value:
      "Mix: 5-15 micros/mids con permiso de whitelisting. Objetivo: anuncios desde la cuenta del creador (mejor CTR) + retarget. Ideal para: performance puro. Clave: negociar derechos y duracion de uso (30/60/90 dias).",
  },
] as const
