/** Display branding — override via NEXT_PUBLIC_APP_NAME in .env.local */
export const APP_NAME =
  process.env.NEXT_PUBLIC_APP_NAME?.trim() ||
  "ICICI Prudential Mutual Funds — Facts Assistant";

export const APP_AMC_LABEL = "ICICI Prudential Mutual Funds";

export const APP_PRODUCT_LABEL = "Facts Assistant";
