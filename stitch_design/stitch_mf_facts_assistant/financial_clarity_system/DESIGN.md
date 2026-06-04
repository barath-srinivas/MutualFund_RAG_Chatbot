---
name: Financial Clarity System
colors:
  surface: '#f8f9fd'
  surface-dim: '#d9dade'
  surface-bright: '#f8f9fd'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3f7'
  surface-container: '#edeef2'
  surface-container-high: '#e7e8ec'
  surface-container-highest: '#e1e2e6'
  on-surface: '#191c1f'
  on-surface-variant: '#3c4a44'
  inverse-surface: '#2e3134'
  inverse-on-surface: '#eff1f5'
  outline: '#6c7a74'
  outline-variant: '#bbcac3'
  surface-tint: '#006b55'
  primary: '#006b55'
  on-primary: '#ffffff'
  primary-container: '#00b894'
  on-primary-container: '#004233'
  inverse-primary: '#4bddb7'
  secondary: '#586062'
  on-secondary: '#ffffff'
  secondary-container: '#dae1e3'
  on-secondary-container: '#5d6466'
  tertiary: '#5e4eb6'
  on-tertiary: '#ffffff'
  tertiary-container: '#a494ff'
  on-tertiary-container: '#38248e'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#6dfad2'
  primary-fixed-dim: '#4bddb7'
  on-primary-fixed: '#002018'
  on-primary-fixed-variant: '#005140'
  secondary-fixed: '#dde4e6'
  secondary-fixed-dim: '#c1c8ca'
  on-secondary-fixed: '#161d1f'
  on-secondary-fixed-variant: '#41484a'
  tertiary-fixed: '#e5deff'
  tertiary-fixed-dim: '#c9bfff'
  on-tertiary-fixed: '#1a0063'
  on-tertiary-fixed-variant: '#46359c'
  background: '#f8f9fd'
  on-background: '#191c1f'
  surface-variant: '#e1e2e6'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  code:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: auto
---

## Brand & Style

The design system is engineered for the modern fintech landscape, prioritizing speed, transparency, and trust. It balances the energetic optimism of high-growth investing with the steady reliability of institutional finance. 

The aesthetic is **Corporate / Modern**, characterized by exceptional legibility, high-contrast action states, and a restrained use of depth. It avoids unnecessary ornamentation to focus the user's attention on data and decision-making. The interface feels "technical but approachable," using a clean light-mode foundation to convey an open and honest atmosphere.

## Colors

The palette is anchored by a vibrant mint green, used exclusively for primary success actions, confirmations, and brand identification. This is contrasted against a deep navy/indigo (Secondary) for text and structural elements to ensure high legibility and an institutional feel.

- **Primary (#00B894):** Use for "Buy" buttons, success states, and primary brand marks.
- **Secondary (#2D3436 / #44329A):** Deep navy for primary headings and indigo for subtle branding accents.
- **Background:** A crisp white (#FFFFFF) is the primary surface, with a light gray (#F2F3F7) used for secondary containers and section backgrounds to create subtle separation.
- **Compliance:** High-contrast reds (#D63031) and oranges (#E17055) are reserved for risk warnings and critical disclosures to meet regulatory accessibility standards.

## Typography

The design system utilizes **Inter** across all levels to maintain a systematic and utilitarian feel. 

- **Weight Strategy:** Use Bold (700) for primary headers to establish clear hierarchy, Semi-Bold (600) for sub-headers and button labels, and Regular (400) for all body copy and data descriptions.
- **Data Display:** For financial figures and tickers, use Semi-Bold weight to ensure the numbers are the most prominent element on the page.
- **Letter Spacing:** Headlines utilize a slight negative tracking to feel tighter and more impactful, while small labels use increased tracking for better readability in uppercase.

## Layout & Spacing

The design system is built on a strict **8px grid system**. All dimensions, padding, and margins must be multiples of 8 to ensure a rigorous and professional alignment.

- **Grid Model:** A 12-column fixed grid for desktop (max-width: 1200px) and a fluid 4-column grid for mobile.
- **Vertical Rhythm:** Use 16px (md) for internal component spacing and 32px (xl) for section-level spacing. 
- **Density:** Maintain a "Clean Professional" density. White space should be used generously between different financial instruments (cards) to prevent visual clutter, but kept tight within components to keep related data points connected.

## Elevation & Depth

This design system uses a **Tonal Layering** approach rather than heavy shadows to maintain a clean, high-performance look.

- **Base Level (Level 0):** The primary background color.
- **Surface Level (Level 1):** White cards or containers used to group content, featuring a subtle 1px border (#E5E7EB) instead of a shadow.
- **Interactive Level (Level 2):** Only used for active dropdowns or modals. A soft, extremely diffused shadow (0px 4px 12px rgba(0, 0, 0, 0.05)) is applied to lift the element off the page.
- **Focus States:** Use a 2px outer glow in the primary mint green color to clearly indicate keyboard navigation and active input.

## Shapes

The shape language is **Soft**, utilizing a 4px (0.25rem) base radius. This provides a modern touch without appearing overly "bubbly" or informal.

- **Standard Elements:** Buttons, input fields, and small cards use the base 4px radius.
- **Large Containers:** Dashboard widgets and main content areas use `rounded-lg` (8px).
- **Interactive Feedback:** Selection states in lists should use the base 4px radius to highlight the active row.

## Components

- **Buttons:** Primary buttons use the mint green background with white text. Secondary buttons use a white background with a navy border and navy text. Use "Large" height (48px) for primary CTAs like "Invest" or "Login."
- **Input Fields:** Use a 1px neutral border. On focus, the border transitions to the secondary indigo. Labels should always be visible above the field in `label-md`.
- **Chips:** Used for stock tags (e.g., "Equity," "Debt"). These should be low-contrast (light gray background with navy text) unless they indicate a status like "High Growth," where they can take on a subtle tint of the primary color.
- **Lists:** Data-heavy lists (holdings, transactions) should use 16px vertical padding with a 1px bottom border separator.
- **Cards:** Used as the primary container for individual stocks or mutual funds. They must include a clear header, a sparkline or data visualization area, and a footer for primary metrics.
- **Search Bar:** A prominent, wide input with a search icon and a "Ctrl+K" keyboard shortcut hint, styled with a soft background to distinguish it from the navigation bar.