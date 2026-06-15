/**
 * SoukPilot S-mark icon using the exact brand SVG.
 * white={true} inverts it to white (for use on coloured backgrounds like the widget FAB).
 */
export default function LogoIcon({
  size = 36,
  white = false,
}: {
  size?: number;
  white?: boolean;
}) {
  return (
    <img
      src="/logo.svg"
      width={size}
      height={size}
      alt="SoukPilot"
      style={{
        objectFit: "contain",
        display: "block",
        ...(white ? { filter: "brightness(0) invert(1)" } : {}),
      }}
    />
  );
}
