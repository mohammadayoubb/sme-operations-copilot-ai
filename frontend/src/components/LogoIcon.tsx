/**
 * SoukPilot brand mark.
 *
 * iconOnly  → just the S-mark icon (for widget FAB / small spaces)
 * default   → full wordmark: [S-icon] + "oukPilot AI"  (icon serves as the S)
 * white     → inverts icon to white (for use on coloured backgrounds)
 */
export default function LogoIcon({
  size = 36,
  iconOnly = false,
  white = false,
}: {
  size?: number;
  iconOnly?: boolean;
  white?: boolean;
}) {
  const icon = (
    <img
      src="/logo-mark.svg"
      width={size}
      height={size}
      alt="S"
      style={{
        objectFit: "contain",
        display: "block",
        flexShrink: 0,
        ...(white ? { filter: "brightness(0) invert(1)" } : {}),
      }}
    />
  );

  if (iconOnly) return icon;

  const textSize = Math.round(size * 0.52);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
      {icon}
      <span
        style={{
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
          fontSize: textSize,
          fontWeight: 800,
          color: white ? "rgba(255,255,255,0.92)" : "rgba(255,255,255,0.92)",
          letterSpacing: "-0.3px",
          lineHeight: 1,
          userSelect: "none",
        }}
      >
        oukPilot{" "}
        <span style={{ color: white ? "rgba(255,255,255,0.7)" : "#818cf8", fontWeight: 700, fontSize: Math.round(textSize * 0.72) }}>
          AI
        </span>
      </span>
    </div>
  );
}
