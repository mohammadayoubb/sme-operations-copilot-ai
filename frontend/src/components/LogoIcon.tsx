export default function LogoIcon({ size = 36, color = "#818cf8" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={Math.round(size * 66 / 70)} viewBox="0 0 70 66" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Hexagon + speech bubble tail */}
      <path
        d="M20 6 L56 6 L64 28 L56 50 L44 50 L38 62 L32 50 L20 50 L12 28 Z"
        stroke={color} strokeWidth="3" strokeLinejoin="round"
        fill="rgba(99,102,241,0.07)"
      />
      {/* Circuit nodes on left */}
      <circle cx="5" cy="22" r="2.5" fill={color} />
      <line x1="7.5" y1="22" x2="12" y2="22" stroke={color} strokeWidth="2" />
      <circle cx="5" cy="34" r="2.5" fill={color} />
      <line x1="7.5" y1="34" x2="14" y2="34" stroke={color} strokeWidth="2" />
      {/* Awning top bar */}
      <rect x="22" y="16" width="26" height="3" rx="1.5" fill={color} />
      {/* Awning scallops */}
      <path
        d="M22 16 Q25 22 28 16 Q31 22 34 16 Q37 22 40 16 Q43 22 46 16 L46 24 Q38 27 30 27 Q24 27 22 24 Z"
        fill={color} fillOpacity="0.6"
      />
      {/* Shop front */}
      <rect x="24" y="29" width="22" height="16" rx="1.5" stroke={color} strokeWidth="2" fill="none" />
      {/* Arched door */}
      <path d="M29 45 L29 38 A6 6 0 0 0 41 38 L41 45" stroke={color} strokeWidth="2" fill="none" />
    </svg>
  );
}
