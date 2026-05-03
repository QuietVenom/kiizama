import authEn from "./locales/en/auth.json"
import billingEn from "./locales/en/billing.json"
import brandIntelligenceEn from "./locales/en/brandIntelligence.json"
import commonEn from "./locales/en/common.json"
import creatorsSearchEn from "./locales/en/creatorsSearch.json"
import dashboardEn from "./locales/en/dashboard.json"
import landingEn from "./locales/en/landing.json"
import settingsEn from "./locales/en/settings.json"
import authEs from "./locales/es/auth.json"
import billingEs from "./locales/es/billing.json"
import brandIntelligenceEs from "./locales/es/brandIntelligence.json"
import commonEs from "./locales/es/common.json"
import creatorsSearchEs from "./locales/es/creatorsSearch.json"
import dashboardEs from "./locales/es/dashboard.json"
import landingEs from "./locales/es/landing.json"
import settingsEs from "./locales/es/settings.json"
import authPtBr from "./locales/pt-BR/auth.json"
import billingPtBr from "./locales/pt-BR/billing.json"
import brandIntelligencePtBr from "./locales/pt-BR/brandIntelligence.json"
import commonPtBr from "./locales/pt-BR/common.json"
import creatorsSearchPtBr from "./locales/pt-BR/creatorsSearch.json"
import dashboardPtBr from "./locales/pt-BR/dashboard.json"
import landingPtBr from "./locales/pt-BR/landing.json"
import settingsPtBr from "./locales/pt-BR/settings.json"

export const resources = {
  es: {
    common: commonEs,
    landing: landingEs,
    auth: authEs,
    settings: settingsEs,
    dashboard: dashboardEs,
    billing: billingEs,
    creatorsSearch: creatorsSearchEs,
    brandIntelligence: brandIntelligenceEs,
  },
  en: {
    common: commonEn,
    landing: landingEn,
    auth: authEn,
    settings: settingsEn,
    dashboard: dashboardEn,
    billing: billingEn,
    creatorsSearch: creatorsSearchEn,
    brandIntelligence: brandIntelligenceEn,
  },
  "pt-BR": {
    common: commonPtBr,
    landing: landingPtBr,
    auth: authPtBr,
    settings: settingsPtBr,
    dashboard: dashboardPtBr,
    billing: billingPtBr,
    creatorsSearch: creatorsSearchPtBr,
    brandIntelligence: brandIntelligencePtBr,
  },
} as const
