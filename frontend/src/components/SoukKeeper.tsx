import { useMemo } from "react";

type MascotState = "idle" | "happy" | "celebrating" | "worried" | "alert";

interface Props {
  loading?: boolean;
  lowStockCount: number;
  pendingCount: number;
  salesChangePct?: number | null;
  driftStatus?: string | null;
}

function deriveState(p: Props): MascotState {
  if (p.loading) return "idle";
  if (p.driftStatus === "alert" || p.lowStockCount > 3) return "alert";
  if ((p.salesChangePct ?? 0) >= 8 && p.lowStockCount === 0) return "celebrating";
  if (p.lowStockCount > 0 || p.driftStatus === "warning" || p.pendingCount > 3) return "worried";
  return "happy";
}

function getMessage(state: MascotState, p: Props): string {
  if (state === "idle") return "Loading your business…";
  if (state === "celebrating") return `Sales up ${p.salesChangePct?.toFixed(1)}%! Mashallah! 🎉`;
  if (state === "happy") {
    if (p.salesChangePct != null && p.salesChangePct > 0)
      return `Up ${p.salesChangePct.toFixed(1)}% this week. Yalla! 👋`;
    return "Business is looking good! Ahlan! 👋";
  }
  if (state === "worried") {
    if (p.lowStockCount > 0)
      return `${p.lowStockCount} item${p.lowStockCount > 1 ? "s" : ""} need restocking.`;
    if (p.pendingCount > 3) return `${p.pendingCount} orders pending review.`;
    return "Keep an eye on sales distribution.";
  }
  if (p.lowStockCount > 3) return `${p.lowStockCount} products critically low!`;
  return "ML drift alert — check the monitor.";
}

const STATE_ANIM: Record<MascotState, string> = {
  idle: "souk-float",
  happy: "souk-float",
  celebrating: "souk-celebrate",
  worried: "souk-shake",
  alert: "souk-alert-pulse",
};

const BUBBLE_COLORS: Record<MascotState, [string, string]> = {
  idle:        ["rgba(129,140,248,0.10)", "rgba(129,140,248,0.30)"],
  happy:       ["rgba(52,211,153,0.10)",  "rgba(52,211,153,0.30)"],
  celebrating: ["rgba(251,191,36,0.12)",  "rgba(251,191,36,0.40)"],
  worried:     ["rgba(251,146,60,0.10)",  "rgba(251,146,60,0.32)"],
  alert:       ["rgba(248,113,113,0.10)", "rgba(248,113,113,0.35)"],
};

export default function SoukKeeper(props: Props) {
  const state = useMemo(() => deriveState(props), [props]);
  const message = getMessage(state, props);
  const [bubbleBg, bubbleBorder] = BUBBLE_COLORS[state];
  const armUp = state === "celebrating";

  const mouthPath: Record<MascotState, string> = {
    idle:        "M33 62 Q40 65 47 62",
    happy:       "M31 61 Q40 69 49 61",
    celebrating: "M29 60 Q40 72 51 60",
    worried:     "M32 66 Q40 61 48 66",
    alert:       "M33 65 Q40 61 47 65",
  };

  const browL = (state === "worried" || state === "alert")
    ? "M27 37 Q32 40 37 37"
    : "M27 35 Q32 33 37 36";

  const browR = (state === "worried" || state === "alert")
    ? "M43 37 Q48 40 53 37"
    : "M43 35 Q48 33 53 36";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      {/* Speech bubble */}
      <div
        className="souk-bubble"
        style={{
          background: bubbleBg,
          border: `1px solid ${bubbleBorder}`,
          borderRadius: 10,
          padding: "8px 13px",
          maxWidth: 190,
          fontSize: 12,
          lineHeight: 1.45,
          color: "rgba(255,255,255,0.85)",
          position: "relative",
          backdropFilter: "blur(6px)",
        }}
      >
        {message}
        <span
          style={{
            position: "absolute",
            right: -7,
            top: "50%",
            transform: "translateY(-50%)",
            width: 0,
            height: 0,
            borderTop: "6px solid transparent",
            borderBottom: "6px solid transparent",
            borderLeft: `7px solid ${bubbleBorder}`,
          }}
        />
      </div>

      {/* Character */}
      <div className={STATE_ANIM[state]} style={{ flexShrink: 0, lineHeight: 0 }}>
        <svg
          viewBox="0 0 80 110"
          width="68"
          height="94"
          xmlns="http://www.w3.org/2000/svg"
          aria-label="Souk Keeper mascot"
        >
          {/* Celebration sparkles */}
          {state === "celebrating" && (
            <>
              <text className="souk-star" x="4" y="32" fontSize="10" fill="#FBBF24">★</text>
              <text className="souk-star-alt" x="63" y="26" fontSize="8" fill="#F59E0B">✦</text>
              <text className="souk-star" x="9" y="18" fontSize="7" fill="#FBBF24">★</text>
            </>
          )}

          {/* Arms */}
          <path
            d={armUp ? "M22 74 C 14 62 10 50 12 40" : "M22 74 C 16 85 12 94 10 100"}
            stroke="#6D28D9"
            strokeWidth="11"
            fill="none"
            strokeLinecap="round"
          />
          <path
            d={armUp ? "M58 74 C 66 62 70 50 68 40" : "M58 74 C 64 85 68 94 70 100"}
            stroke="#6D28D9"
            strokeWidth="11"
            fill="none"
            strokeLinecap="round"
          />

          {/* Body */}
          <path d="M22 70 C 18 88 18 109 40 109 C 62 109 62 88 58 70 Z" fill="#7C3AED" />
          {/* Chest detail */}
          <path d="M35 70 L40 79 L45 70" fill="#5B21B6" opacity="0.7" />

          {/* Hands */}
          <circle
            cx={armUp ? 12 : 10}
            cy={armUp ? 39 : 99}
            r="6"
            fill="#F5C09A"
            stroke="#E0A070"
            strokeWidth="0.5"
          />
          <circle
            cx={armUp ? 68 : 70}
            cy={armUp ? 39 : 99}
            r="6"
            fill="#F5C09A"
            stroke="#E0A070"
            strokeWidth="0.5"
          />

          {/* Head */}
          <circle cx="40" cy="50" r="23" fill="#F5C09A" stroke="#E0A070" strokeWidth="0.5" />

          {/* Blush cheeks */}
          {(state === "happy" || state === "celebrating") && (
            <>
              <ellipse cx="24" cy="56" rx="5" ry="3" fill="#FFAA9F" opacity="0.45" />
              <ellipse cx="56" cy="56" rx="5" ry="3" fill="#FFAA9F" opacity="0.45" />
            </>
          )}

          {/* Sweat drop */}
          {(state === "worried" || state === "alert") && (
            <ellipse cx="59" cy="42" rx="3" ry="4.5" fill="#93C5FD" opacity="0.8" />
          )}

          {/* Eyebrows */}
          <path d={browL} stroke="#8B6047" strokeWidth="2" fill="none" strokeLinecap="round" />
          <path d={browR} stroke="#8B6047" strokeWidth="2" fill="none" strokeLinecap="round" />

          {/* Eyes — three distinct expressions */}
          {state === "alert" ? (
            <>
              <ellipse cx="33" cy="47" rx="7.5" ry="8.5" fill="white" />
              <circle cx="33" cy="48" r="4" fill="#1A0A00" />
              <circle cx="34.5" cy="46" r="1.2" fill="white" />
              <ellipse cx="47" cy="47" rx="7.5" ry="8.5" fill="white" />
              <circle cx="47" cy="48" r="4" fill="#1A0A00" />
              <circle cx="48.5" cy="46" r="1.2" fill="white" />
            </>
          ) : state === "worried" ? (
            <>
              <ellipse cx="33" cy="47" rx="6" ry="5" fill="white" />
              <circle cx="33" cy="47" r="3" fill="#1A0A00" />
              <circle cx="34" cy="46" r="0.8" fill="white" />
              <ellipse cx="47" cy="47" rx="6" ry="5" fill="white" />
              <circle cx="47" cy="47" r="3" fill="#1A0A00" />
              <circle cx="48" cy="46" r="0.8" fill="white" />
            </>
          ) : (
            <>
              <ellipse cx="33" cy="47" rx="6" ry="7" fill="white" />
              <circle cx="34" cy="48" r="3.5" fill="#1A0A00" />
              <circle cx="35.5" cy="46" r="1" fill="white" />
              <ellipse cx="47" cy="47" rx="6" ry="7" fill="white" />
              <circle cx="48" cy="48" r="3.5" fill="#1A0A00" />
              <circle cx="49.5" cy="46" r="1" fill="white" />
            </>
          )}

          {/* Mustache */}
          <path
            d="M33 57 Q36 59.5 40 57.5 Q44 59.5 47 57"
            stroke="#8B6047"
            strokeWidth="1.5"
            fill="none"
            strokeLinecap="round"
          />

          {/* Mouth */}
          <path
            d={mouthPath[state]}
            stroke="#B05030"
            strokeWidth="2.5"
            fill="none"
            strokeLinecap="round"
          />
          {/* Teeth for celebrating */}
          {state === "celebrating" && (
            <path
              d="M33 63 Q40 69 47 63 Q47 68 40 68 Q33 68 33 63"
              fill="white"
              opacity="0.85"
            />
          )}

          {/* Fez (tarboosh) — drawn last so it sits on top of head */}
          <ellipse cx="40" cy="28" rx="26" ry="7" fill="#991B1B" />
          <rect x="17" y="10" width="46" height="19" rx="5" fill="#DC2626" />
          <ellipse cx="40" cy="10" rx="22" ry="5.5" fill="#EF4444" />
          {/* Tassel */}
          <line x1="57" y1="10" x2="64" y2="3" stroke="#D97706" strokeWidth="1.5" />
          <circle cx="64" cy="3" r="4" fill="#D97706" />
          <circle cx="64" cy="3" r="2" fill="#F59E0B" />
        </svg>
      </div>
    </div>
  );
}
