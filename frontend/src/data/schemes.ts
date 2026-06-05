/** Mirrors corpus/schemes.yaml — used for scheme picker only. */
export type Scheme = {
  scheme_id: string;
  display_name: string;
  category: string;
};

export const SCHEMES: Scheme[] = [
  {
    scheme_id: "icici-large-cap",
    display_name: "ICICI Prudential Large Cap Fund Direct Growth",
    category: "Equity · Large Cap",
  },
  {
    scheme_id: "icici-manufacturing",
    display_name: "ICICI Prudential Manufacturing Fund Direct Growth",
    category: "Equity · Sectoral",
  },
  {
    scheme_id: "icici-phd",
    display_name:
      "ICICI Prudential Pharma Healthcare and Diagnostics (P.H.D) Fund Direct Growth",
    category: "Equity · Sectoral",
  },
  {
    scheme_id: "icici-us-bluechip",
    display_name: "ICICI Prudential US Bluechip Equity Fund Direct Growth",
    category: "Equity · International",
  },
  {
    scheme_id: "icici-multi-asset",
    display_name: "ICICI Prudential Multi Asset Fund Direct Growth",
    category: "Hybrid · Multi Asset Allocation",
  },
  {
    scheme_id: "icici-nifty-auto",
    display_name: "ICICI Prudential Nifty Auto Index Fund Direct Growth",
    category: "Equity · Thematic",
  },
  {
    scheme_id: "icici-nifty-50",
    display_name: "ICICI Prudential Nifty 50 Index Direct Plan Growth",
    category: "Equity · Large Cap",
  },
  {
    scheme_id: "icici-nifty-500",
    display_name: "ICICI Prudential Nifty 500 Index Fund Direct Growth",
    category: "Equity · Large Cap",
  },
  {
    scheme_id: "icici-nifty-bank",
    display_name: "ICICI Prudential Nifty Bank Index Fund Direct Growth",
    category: "Equity · Sectoral",
  },
  {
    scheme_id: "icici-nifty-smallcap-250",
    display_name:
      "ICICI Prudential Nifty Smallcap 250 Index Fund Direct Growth",
    category: "Equity · Small Cap",
  },
];
