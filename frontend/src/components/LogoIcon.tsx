import { useRef } from "react";

/**
 * SoukPilot S-mark icon.
 *
 * filled=true  → gradient-filled hex with white interior (default, for dark backgrounds)
 * filled=false → outlined version (for use on already-coloured backgrounds like the widget FAB)
 */
export default function LogoIcon({
  size = 36,
  filled = true,
  color = "rgba(255,255,255,0.95)",
}: {
  size?: number;
  filled?: boolean;
  color?: string;
}) {
  const uid = useRef(`sp${Math.random().toString(36).slice(2, 8)}`).current;
  const h = Math.round((size * 72) / 70);

  // Shared hex + bubble path
  const hexPath =
    "M20 4 L56 4 L66 20 L66 44 L56 56 L44 56 L38 64 L32 56 L20 56 L10 44 L10 20 Z";

  // Awning scallops (hangs downward from top bar)
  const awningPath =
    "M16 13 Q19.5 20 23 13 Q26.5 20 30 13 Q33.5 20 37 13 Q40.5 20 44 13 Q47.5 20 51 13 Q54.5 20 58 13 L58 23 Q48 27 38 27 Q28 27 16 23 Z";

  // Arched door (counterclockwise arc curves upward)
  const doorPath = "M27 50 L27 40 A11 9 0 0 0 49 40 L49 50";

  if (!filled) {
    // Outline variant — used on coloured FAB button
    return (
      <svg width={size} height={h} viewBox="0 0 70 72" fill="none">
        <path d={hexPath} stroke={color} strokeWidth="3" strokeLinejoin="round" fillOpacity="0.12" fill={color} />
        {/* Circuit nodes */}
        <circle cx="4" cy="26" r="2.5" fill={color} />
        <line x1="6.5" y1="26" x2="10" y2="26" stroke={color} strokeWidth="2" />
        <circle cx="4" cy="36" r="2.5" fill={color} />
        <line x1="6.5" y1="36" x2="10" y2="36" stroke={color} strokeWidth="2" />
        {/* Awning bar */}
        <rect x="16" y="10" width="44" height="3" rx="1.5" fill={color} />
        {/* Awning scallops */}
        <path d={awningPath} fill={color} fillOpacity="0.65" />
        {/* Shop front */}
        <rect x="19" y="29" width="38" height="21" rx="2" stroke={color} strokeWidth="2" fill="none" />
        {/* Arch door */}
        <path d={doorPath} stroke={color} strokeWidth="2" fill="none" />
      </svg>
    );
  }

  // Filled variant — gradient hex with white details
  return (
    <svg width={size} height={h} viewBox="0 0 70 72" fill="none">
      <defs>
        <linearGradient id={uid} x1="10" y1="4" x2="66" y2="65" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#818CF8" />
          <stop offset="100%" stopColor="#4338CA" />
        </linearGradient>
      </defs>
      {/* Hex body — gradient fill */}
      <path d={hexPath} fill={`url(#${uid})`} />
      {/* Circuit nodes */}
      <circle cx="4" cy="26" r="3" fill="rgba(255,255,255,0.92)" />
      <line x1="7" y1="26" x2="10" y2="26" stroke="rgba(255,255,255,0.92)" strokeWidth="2" />
      <circle cx="4" cy="36" r="3" fill="rgba(255,255,255,0.92)" />
      <line x1="7" y1="36" x2="10" y2="36" stroke="rgba(255,255,255,0.92)" strokeWidth="2" />
      {/* Awning top bar */}
      <rect x="16" y="10" width="44" height="4" rx="2" fill="rgba(255,255,255,0.95)" />
      {/* Awning scallops */}
      <path d={awningPath} fill="rgba(255,255,255,0.82)" />
      {/* Shop front */}
      <rect x="19" y="29" width="38" height="21" rx="2" stroke="rgba(255,255,255,0.88)" strokeWidth="2" fill="rgba(255,255,255,0.08)" />
      {/* Arch door */}
      <path d={doorPath} stroke="rgba(255,255,255,0.92)" strokeWidth="2" fill="none" />
    </svg>
  );
}
