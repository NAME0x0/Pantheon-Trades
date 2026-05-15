/**
 * CDN URLs for all external imagery + iconography.
 *
 * We do not host any of these locally — they are served by Iconify
 * (icons), Unsplash (photography), and Wikimedia Commons (public-domain
 * classical art). Keeping them in one place means a CDN swap is a
 * single-file change.
 */

/** Iconify Greek-temple line-art mark, gold-tinted. Used as the brand mark. */
export const BRAND_MARK =
  "https://api.iconify.design/game-icons/greek-temple.svg?color=%23d4a85e";

/** Smaller tinted accents — used across the site. */
export const ICON = {
  owl: "https://api.iconify.design/game-icons/owl.svg?color=%23d4a85e",
  laurel: "https://api.iconify.design/game-icons/laurel-crown.svg?color=%23d4a85e",
  scales: "https://api.iconify.design/game-icons/scales.svg?color=%23d4a85e",
  column: "https://api.iconify.design/game-icons/greek-temple.svg?color=%23d4a85e",
  helmet: "https://api.iconify.design/game-icons/spartan-helmet.svg?color=%23d4a85e",
} as const;

/** Unsplash photographs. All URLs include format + width + quality
 * params so we never pay for full-res over the wire. */
const U = (id: string, w = 2000, q = 70) =>
  `https://images.unsplash.com/${id}?auto=format&fit=crop&w=${w}&q=${q}`;

export const PHOTO = {
  // Parthenon at golden hour — used full-bleed behind the hero.
  parthenon: U("photo-1555993539-1732b0258235", 2400, 80),
  // Classical sculpture, dramatic lighting — Proof of Restraint section.
  bust: U("photo-1564399579883-451a5d44ec08", 1800),
  // White marble close-up — texture overlay for sections / cards.
  marble: U("photo-1604147495798-57beb5d6af73", 1600),
  // Weathered stone temple ruin — agent roster backdrop.
  ruin: U("photo-1502602898657-3e91760cbb34", 1800),
  // Cracked marble — for restraint / oxblood moments.
  cracked: U("photo-1582571504057-7e5a5d1e0e0a", 1400),
  // Greek temple columns rising into sky — premise section.
  columns: U("photo-1603565816030-6b389eeb23cb", 1800),
  // Aged statue head, side-profile — agent roster column.
  profile: U("photo-1569335468445-c061686ad931", 1600),
  // Olympia ruins at dusk — vote simulator backdrop.
  olympia: U("photo-1556715037-7b81f3a51e58", 1800),
  // Carved stone relief detail — pipeline section accent.
  relief: U("photo-1542401886-65d6c61db217", 1400),
  // Athenian acropolis aerial — closing CTA.
  acropolis: U("photo-1603565816030-6b389eeb23cb", 2200, 75),
} as const;
