export const BRAND_INTELLIGENCE_LIMITS = {
  audience: 5,
  brandUrls: 3,
  campaignProfiles: 15,
  collaborators: 10,
  creatorUrls: 3,
  primaryPlatforms: 6,
  reputationSignalCharacters: 30,
} as const

export const CAMPAIGN_FIELD_HELP = {
  audience: "Audiencias objetivo de la campana.",
  brand_context: "Contexto general de la marca (max 250 caracteres).",
  brand_goals_context:
    "Contexto adicional del goal de marca (max 250 caracteres).",
  brand_goals_type: "Goal principal de marca.",
  brand_name: "Nombre de la marca.",
  brand_urls: "Lista de URLs de marca (max 3).",
  campaign_type: "Estrategia de campana seleccionada.",
  profiles_list: "Lista de usernames de creators (max 15).",
  timeframe: "Horizonte temporal de la campana.",
} as const

export const CREATOR_FIELD_HELP = {
  audience: "Audiencias objetivo.",
  collaborators_list: "Lista de colaboradores relevantes (max 10).",
  creator_context: "Contexto general del creador.",
  creator_urls: "Lista de URLs del creador (max 3).",
  creator_username: "Username del creador.",
  goal_context: "Contexto adicional del goal de reputacion.",
  goal_type: "Goal principal de reputacion para creator strategy.",
  primary_platforms: "Plataformas principales del creador.",
  reputation_signals:
    "Senales de reputacion con opciones: strengths, weaknesses, incidents, concerns.",
  timeframe: "Horizonte temporal de la estrategia.",
} as const

export const REPUTATION_SIGNAL_FIELD_HELP = {
  concerns:
    "Concerns dentro de las senales de reputacion para destacar riesgos o tensiones activas.",
  incidents:
    "Incidents dentro de las senales de reputacion para registrar hechos o episodios relevantes.",
  strengths:
    "Strengths dentro de las senales de reputacion para destacar activos reputacionales.",
  weaknesses:
    "Weaknesses dentro de las senales de reputacion para registrar fricciones o puntos vulnerables.",
} as const
