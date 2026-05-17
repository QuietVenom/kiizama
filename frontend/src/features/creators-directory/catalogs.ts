export const CREATOR_DIRECTORY_CATEGORY_OPTIONS = [
  "Lifestyle",
  "Fashion",
  "Beauty / Skincare / Makeup",
  "Fitness / Wellness",
  "Health / Nutrition",
  "Foodie / Gastronomy / Cooking",
  "Travel",
  "Technology / Gadgets",
  "Gaming / Esports / Streaming",
  "Business / Finance / Entrepreneurship",
  "Education / Outreach",
  "Motherhood / Family / Parenting",
  "Pets / Animals",
  "Art / Design / Photography / Illustration",
  "Music / Dance / Entertainment",
  "Cars / Motorcycles",
  "Activism / Environment / Politics",
  "Humor / Comedy",
  "Pop Culture / Anime / K-Pop",
  "Spirituality / Mindfulness",
] as const

export const CREATOR_DIRECTORY_ROLE_OPTIONS = [
  "Expert / Professional / Authority",
  "Aspirational / Lifestyle",
  "Entertainment",
  "Inspirational / Motivational",
  "Critic / Reviewer",
  "Educator / Communicator",
  "Activist / Social Cause",
  "UGC Creator",
  "Testimonial / Personal Opinion",
] as const

export const CREATOR_DIRECTORY_RANGE_PRESETS = [
  { key: "nano", label: "Nano (1k-10k)", min: 1_000, max: 9_999 },
  { key: "micro", label: "Micro (10k-100k)", min: 10_000, max: 99_999 },
  {
    key: "mid_tier",
    label: "Mid-tier (100k-500k)",
    min: 100_000,
    max: 499_999,
  },
  { key: "macro", label: "Macro (500k-1M)", min: 500_000, max: 999_999 },
  { key: "mega", label: "Mega (1M+)", min: 1_000_000, max: null },
] as const

export const CREATOR_DIRECTORY_SORT_OPTIONS = [
  {
    value: "username",
    labelKey: "directoryPreview.filters.sortDialog.options.username",
  },
  {
    value: "follower_count",
    labelKey: "directoryPreview.filters.sortDialog.options.followerCount",
  },
] as const
