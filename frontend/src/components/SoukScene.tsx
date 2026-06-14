import { useEffect, useMemo, useState } from "react";

type TimeOfDay = "night" | "dawn" | "day" | "dusk";

interface Props {
  lowStockCount: number;
  pendingCount: number;
  salesChangePct?: number | null;
  loading?: boolean;
}

function getTimeOfDay(h: number): TimeOfDay {
  if (h >= 5  && h < 7)  return "dawn";
  if (h >= 7  && h < 18) return "day";
  if (h >= 18 && h < 20) return "dusk";
  return "night";
}

const SKY: Record<TimeOfDay, string> = {
  night: "#040610",
  dawn:  "#0d1230",
  day:   "#0d2a5a",
  dusk:  "#1a0824",
};

const HORIZON: Record<TimeOfDay, string> = {
  night: "#06091a",
  dawn:  "#4a1a20",
  day:   "#0d3a7a",
  dusk:  "#4a1030",
};

function celestial(h: number) {
  const isDay = h >= 6 && h < 20;
  const progress = isDay
    ? (h - 6) / 14
    : h >= 20
    ? (h - 20) / 10
    : (h + 4) / 10;
  const p = Math.max(0, Math.min(1, progress));
  return {
    x: 40 + p * 720,
    y: 105 - Math.sin(p * Math.PI) * 82,
    isDay,
  };
}

const STARS = [
  [95,15],[180,42],[265,12],[355,33],[445,16],[535,48],
  [625,20],[710,38],[750,10],[130,55],[480,55],[320,8],
  [590,36],[58,40],[770,28],
];

export default function SoukScene({ lowStockCount, pendingCount, salesChangePct, loading }: Props) {
  const [hour, setHour] = useState(() => new Date().getHours());
  useEffect(() => {
    const id = setInterval(() => setHour(new Date().getHours()), 60_000);
    return () => clearInterval(id);
  }, []);

  const tod       = getTimeOfDay(hour);
  const { x: cx, y: cy, isDay } = celestial(hour);
  const showStars = tod === "night" || tod === "dawn" || tod === "dusk";

  const activityLevel = useMemo(() => {
    if (loading) return 1;
    let l = 1;
    if (pendingCount > 0) l++;
    if ((salesChangePct ?? 0) > 5) l++;
    return Math.min(l, 3);
  }, [loading, pendingCount, salesChangePct]);

  const timeLabel = {
    night: "◗ night market",
    dawn:  "◒ sunrise",
    day:   "◑ open market",
    dusk:  "◒ golden hour",
  }[tod];

  return (
    <div style={{
      width: "100%",
      borderRadius: 12,
      overflow: "hidden",
      marginBottom: 24,
      border: "1px solid rgba(255,255,255,0.07)",
      flexShrink: 0,
    }}>
      <svg
        viewBox="0 0 800 155"
        width="100%"
        xmlns="http://www.w3.org/2000/svg"
        aria-label="Live souk market scene"
        style={{ display: "block" }}
      >
        {/* ── Sky ── */}
        <rect x="0" y="0" width="800" height="118" fill={SKY[tod]}/>
        <rect x="0" y="94" width="800" height="24" fill={HORIZON[tod]} opacity="0.55"/>

        {/* ── Stars ── */}
        {showStars && STARS.map(([sx, sy], i) => (
          <circle
            key={i} cx={sx} cy={sy}
            r={i % 3 === 0 ? 1.5 : 1}
            fill="white"
            opacity={tod === "night" ? 0.55 : 0.22}
          />
        ))}

        {/* ── Sun or Moon ── */}
        {isDay ? (
          <>
            <circle cx={cx} cy={cy} r="19" fill="#FCD34D" opacity="0.9"/>
            <circle cx={cx} cy={cy} r="27" fill="#FCD34D" opacity="0.1"/>
          </>
        ) : (
          <>
            <circle cx={cx} cy={cy} r="13" fill="#CBD5E1" opacity="0.82"/>
            <circle cx={cx + 5} cy={cy - 3} r="10" fill={SKY[tod]} opacity="0.96"/>
          </>
        )}

        {/* ── Ground ── */}
        <rect x="0" y="115" width="800" height="40" fill="#100c22"/>
        {/* Pavement */}
        <rect x="0" y="125" width="800" height="13" fill="#0d0a1e"/>
        {/* Pavement joints */}
        {[130, 310, 500, 670].map(lx => (
          <line key={lx} x1={lx} y1="125" x2={lx + 28} y2="125"
            stroke="rgba(255,255,255,0.055)" strokeWidth="1.5" strokeDasharray="5,4"/>
        ))}

        {/* ── Market Stalls ── */}
        <Stall x={38}  label="INVOICES"  color="#818cf8" active={!loading} alert={false}/>
        <Stall x={208} label="ORDERS"    color="#34d399" active={pendingCount > 0} alert={pendingCount > 0}/>
        <Stall x={468} label="INVENTORY" color="#fb923c" active={true}       alert={lowStockCount > 0}/>
        <Stall x={638} label="REPORTS"   color="#a78bfa" active={!loading}   alert={false}/>

        {/* ── Walking people ── */}
        <g style={{ animation: "souk-walk-right 16s linear infinite", willChange: "transform" }}>
          <Walker cy={119} color="#818cf8"/>
        </g>
        <g style={{ animation: "souk-walk-left 21s linear infinite 5s", willChange: "transform" }}>
          <Walker cy={119} color="#a78bfa"/>
        </g>
        {activityLevel >= 2 && (
          <g style={{ animation: "souk-walk-right 13s linear infinite 8s", willChange: "transform" }}>
            <Walker cy={121} color="#34d399"/>
          </g>
        )}
        {activityLevel >= 3 && (
          <g style={{ animation: "souk-walk-left 18s linear infinite 2s", willChange: "transform" }}>
            <Walker cy={120} color="#fb923c"/>
          </g>
        )}

        {/* ── Scene label ── */}
        <text x="796" y="151" textAnchor="end" fontSize="8"
          fill="rgba(255,255,255,0.18)"
          fontFamily="Inter, system-ui, sans-serif"
          letterSpacing="0.3">
          {timeLabel}
        </text>
      </svg>
    </div>
  );
}

// ── Stall ────────────────────────────────────────────────────────────────────

function Stall({ x, label, color, active, alert }: {
  x: number; label: string; color: string;
  active: boolean; alert: boolean;
}) {
  const w = 108;
  const top = 60;
  const awH = 17;

  return (
    <g>
      {active && (
        <ellipse
          cx={x + w / 2} cy={top + 28}
          rx={w / 2 + 12} ry={28}
          fill={color} opacity="0.07"
          className="souk-stall-glow"
        />
      )}

      {/* Back wall */}
      <rect x={x} y={top} width={w} height={55} rx="3"
        fill="rgba(255,255,255,0.055)"
        stroke="rgba(255,255,255,0.09)" strokeWidth="0.5"/>

      {/* Shelf lines */}
      <line x1={x+8} y1={top+20} x2={x+w-8} y2={top+20}
        stroke="rgba(255,255,255,0.065)" strokeWidth="0.5"/>
      <line x1={x+8} y1={top+38} x2={x+w-8} y2={top+38}
        stroke="rgba(255,255,255,0.065)" strokeWidth="0.5"/>

      {/* Counter ledge */}
      <rect x={x} y={top+47} width={w} height={8} rx="0"
        fill="rgba(255,255,255,0.075)" stroke="rgba(255,255,255,0.09)" strokeWidth="0.5"/>

      {/* Awning */}
      <polygon
        points={`${x-6},${top} ${x+w+6},${top} ${x+w},${top+awH} ${x},${top+awH}`}
        fill={color}
        opacity={active ? 0.78 : 0.22}
      />
      {/* Awning stripes */}
      {[0,1,2,3].map(i => (
        <line key={i}
          x1={x + 18 + i * 24} y1={top}
          x2={x + 11 + i * 24} y2={top + awH}
          stroke="rgba(0,0,0,0.18)" strokeWidth="5"/>
      ))}

      {/* Support posts */}
      <line x1={x+7}   y1={top+awH} x2={x+7}   y2={top+55}
        stroke="rgba(255,255,255,0.18)" strokeWidth="1.5"/>
      <line x1={x+w-7} y1={top+awH} x2={x+w-7} y2={top+55}
        stroke="rgba(255,255,255,0.18)" strokeWidth="1.5"/>

      {/* Alert badge */}
      {alert && (
        <circle cx={x+w-10} cy={top+8} r="4.5"
          fill="#f87171" className="souk-alert-dot"/>
      )}

      {/* Label */}
      <text x={x + w/2} y={top + 67}
        textAnchor="middle" fontSize="7.5"
        fill={active ? color : "rgba(255,255,255,0.18)"}
        fontFamily="Inter, system-ui, sans-serif"
        fontWeight="700" letterSpacing="0.8">
        {label}
      </text>
    </g>
  );
}

// ── Walker ───────────────────────────────────────────────────────────────────

function Walker({ cy, color }: { cy: number; color: string }) {
  return (
    <>
      <circle cx="8" cy={cy - 24} r="5" fill="#F5C09A"/>
      <rect x="4" y={cy - 18} width="8" height="12" rx="2" fill={color} opacity="0.88"/>
      <line x1="6" y1={cy - 6} x2="4.5" y2={cy + 3}
        stroke={color} strokeWidth="2.5" strokeLinecap="round" opacity="0.78"/>
      <line x1="10" y1={cy - 6} x2="11.5" y2={cy + 3}
        stroke={color} strokeWidth="2.5" strokeLinecap="round" opacity="0.78"/>
    </>
  );
}
