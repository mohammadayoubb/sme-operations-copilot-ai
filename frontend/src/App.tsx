import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState, createContext, useContext } from "react";
import Login from "./pages/Login";
import Register from "./pages/Register";
import SuperAdmin from "./pages/SuperAdmin";
import Dashboard from "./pages/Dashboard";
import InvoiceUpload from "./pages/InvoiceUpload";
import Orders from "./pages/Orders";
import Inventory from "./pages/Inventory";
import PricingAdvisor from "./pages/PricingAdvisor";
import BusinessQA from "./pages/BusinessQA";
import Reports from "./pages/Reports";
import VoiceAssistant from "./pages/VoiceAssistant";
import AgentChat from "./pages/AgentChat";
import WidgetChat from "./pages/WidgetChat";
import WidgetSettings from "./pages/WidgetSettings";

// ── SVG icon helper ──────────────────────────────────────────────────────────

function NavIcon({ children }: { children: React.ReactNode }) {
  return (
    <svg
      width="15" height="15" viewBox="0 0 16 16"
      fill="none" stroke="currentColor"
      strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}

const IC = {
  dashboard: (
    <NavIcon>
      <rect x="1" y="1" width="6" height="6" rx="1.2" />
      <rect x="9" y="1" width="6" height="6" rx="1.2" />
      <rect x="1" y="9" width="6" height="6" rx="1.2" />
      <rect x="9" y="9" width="6" height="6" rx="1.2" />
    </NavIcon>
  ),
  invoices: (
    <NavIcon>
      <path d="M9 1.5H4a1 1 0 00-1 1v11a1 1 0 001 1h8a1 1 0 001-1V6L9 1.5z" />
      <path d="M9 1.5V6H13" />
      <line x1="5" y1="9" x2="11" y2="9" />
      <line x1="5" y1="11.5" x2="9" y2="11.5" />
    </NavIcon>
  ),
  orders: (
    <NavIcon>
      <path d="M1.5 2.5h2l2 7h7l1.5-4.5H5.5" />
      <circle cx="7.5" cy="13" r="1" fill="currentColor" stroke="none" />
      <circle cx="12.5" cy="13" r="1" fill="currentColor" stroke="none" />
    </NavIcon>
  ),
  inventory: (
    <NavIcon>
      <path d="M2 6l6-4 6 4v6l-6 4-6-4V6z" />
      <path d="M8 2v12M2 6l6 4 6-4" />
    </NavIcon>
  ),
  pricing: (
    <NavIcon>
      <path d="M2 12L5.5 8l3 3L14 4" />
      <path d="M11 4h3v3" />
    </NavIcon>
  ),
  qa: (
    <NavIcon>
      <path d="M13.5 3H3a1 1 0 00-1 1v6a1 1 0 001 1h2v3l3-3h5.5a1 1 0 001-1V4a1 1 0 00-1-1z" />
    </NavIcon>
  ),
  reports: (
    <NavIcon>
      <line x1="1" y1="14.5" x2="15" y2="14.5" />
      <rect x="2" y="8" width="3" height="6.5" rx=".5" />
      <rect x="6.5" y="4" width="3" height="10.5" rx=".5" />
      <rect x="11" y="6" width="3" height="8.5" rx=".5" />
    </NavIcon>
  ),
  voice: (
    <NavIcon>
      <rect x="5" y="1" width="6" height="8" rx="3" />
      <path d="M2.5 8a5.5 5.5 0 0011 0" />
      <line x1="8" y1="13.5" x2="8" y2="15" />
      <line x1="5.5" y1="15" x2="10.5" y2="15" />
    </NavIcon>
  ),
  agent: (
    <NavIcon>
      <rect x="4" y="4" width="8" height="8" rx="1.5" />
      <path d="M6 4V2.5M10 4V2.5M6 12v1.5M10 12v1.5M4 6H2.5M4 10H2.5M12 6h1.5M12 10h1.5" />
      <circle cx="6.5" cy="8" r=".7" fill="currentColor" stroke="none" />
      <circle cx="9.5" cy="8" r=".7" fill="currentColor" stroke="none" />
    </NavIcon>
  ),
  widget: (
    <NavIcon>
      <rect x="2" y="2" width="12" height="12" rx="2" />
      <path d="M5 8h6M8 5v6" />
    </NavIcon>
  ),
};

// ── Navigation groups ────────────────────────────────────────────────────────

const NAV_GROUPS = [
  {
    label: null,
    items: [
      { to: "/", label: "Dashboard", icon: IC.dashboard },
    ],
  },
  {
    label: "Operations",
    items: [
      { to: "/invoices",  label: "Invoices",  icon: IC.invoices  },
      { to: "/orders",    label: "Orders",    icon: IC.orders    },
      { to: "/inventory", label: "Inventory", icon: IC.inventory },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { to: "/pricing", label: "Pricing Advisor", icon: IC.pricing },
      { to: "/qa",      label: "Business Q&A",    icon: IC.qa      },
      { to: "/reports", label: "Reports",         icon: IC.reports },
    ],
  },
  {
    label: "AI Studio",
    items: [
      { to: "/agent",   label: "AI Agent",      icon: IC.agent  },
      { to: "/voice",   label: "Voice",         icon: IC.voice  },
      { to: "/widget-settings", label: "Widget Embed", icon: IC.widget },
    ],
  },
];

// ── Mobile nav ───────────────────────────────────────────────────────────────

const MobileNavCtx = createContext<{
  isMobile: boolean;
  open: boolean;
  toggle: () => void;
  close: () => void;
}>({ isMobile: false, open: false, toggle: () => {}, close: () => {} });

function useIsMobile() {
  const [v, setV] = useState(() => window.innerWidth < 768);
  useEffect(() => {
    const fn = () => setV(window.innerWidth < 768);
    window.addEventListener("resize", fn);
    return () => window.removeEventListener("resize", fn);
  }, []);
  return v;
}

// ── Topbar ───────────────────────────────────────────────────────────────────

function useClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);
  return now;
}

type SystemStatus = "live" | "degraded" | "offline";


const STATUS_CYCLE: SystemStatus[] = ["live", "degraded", "offline"];

function useSystemStatus(): [SystemStatus, () => void] {
  const [override, setOverride] = useState<SystemStatus | null>(null);
  const [real, setReal] = useState<SystemStatus>("live");

  useEffect(() => {
    const BASE = (import.meta.env.VITE_API_URL as string) ?? "";

    async function check() {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 5000);
      try {
        const res = await fetch(`${BASE}/health`, { signal: controller.signal });
        clearTimeout(timer);
        if (!res.ok) { setReal("offline"); return; }
        const data = await res.json();
        setReal(data.database === "connected" ? "live" : "degraded");
      } catch {
        clearTimeout(timer);
        setReal("offline");
      }
    }

    check();
    const id = setInterval(check, 30_000);
    return () => clearInterval(id);
  }, []);

  function cycle() {
    setOverride((prev) => {
      const current = prev ?? real;
      const next = STATUS_CYCLE[(STATUS_CYCLE.indexOf(current) + 1) % STATUS_CYCLE.length];
      // If we've cycled back to what the real status is, clear the override
      return next === real ? null : next;
    });
  }

  return [override ?? real, cycle];
}

function useBreadcrumb(pathname: string) {
  for (const g of NAV_GROUPS) {
    for (const item of g.items) {
      const matched = item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
      if (matched) return { group: g.label, page: item.label };
    }
  }
  return { group: null, page: "—" };
}

const STATUS_CONFIG: Record<SystemStatus, { label: string; color: string; bg: string; border: string }> = {
  live:     { label: "Live",     color: "#34d399", bg: "rgba(52,211,153,0.07)",  border: "rgba(52,211,153,0.2)"  },
  degraded: { label: "Degraded", color: "#fb923c", bg: "rgba(251,146,60,0.07)",  border: "rgba(251,146,60,0.2)"  },
  offline:  { label: "Offline",  color: "#f87171", bg: "rgba(248,113,113,0.07)", border: "rgba(248,113,113,0.2)" },
};

function Topbar() {
  const location = useLocation();
  const now = useClock();
  const [systemStatus, cycleStatus] = useSystemStatus();
  const { group, page } = useBreadcrumb(location.pathname);
  const { isMobile, toggle } = useContext(MobileNavCtx);

  const time = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
  const date = now.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });

  const sc = STATUS_CONFIG[systemStatus];

  return (
    <header style={{ ...S.topbar, padding: isMobile ? "0 16px" : "0 36px" }}>
      <div style={{ ...S.topbarLeft, gap: isMobile ? 10 : 0 }}>
        {isMobile && (
          <button onClick={toggle} style={S.hamburgerBtn} aria-label="Open menu">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <line x1="2" y1="4.5" x2="16" y2="4.5" />
              <line x1="2" y1="9" x2="16" y2="9" />
              <line x1="2" y1="13.5" x2="16" y2="13.5" />
            </svg>
          </button>
        )}
        {group && (
          <>
            <span style={S.crumbGroup}>{group}</span>
            <span style={S.crumbSep}>·</span>
          </>
        )}
        <span style={S.crumbPage}>{page}</span>
      </div>
      <div style={S.topbarRight}>
        {!isMobile && <span style={S.topbarDate}>{date}</span>}
        <span style={S.topbarTime}>{time}</span>
        <div
          onClick={cycleStatus}
          title="Click to demo system states"
          style={{ ...S.liveChip, background: sc.bg, border: `1px solid ${sc.border}`, cursor: "pointer" }}
        >
          <span style={{
            ...S.liveDot,
            background: sc.color,
            animation: systemStatus === "live" ? "live-pulse 2.5s ease-in-out infinite" : "none",
          }} />
          {!isMobile && <span style={{ ...S.liveLabel, color: sc.color }}>{sc.label}</span>}
        </div>
      </div>
    </header>
  );
}

// ── Logout button ────────────────────────────────────────────────────────────

function LogoutButton() {
  const navigate = useNavigate();
  function logout() {
    localStorage.removeItem("soukpilot_token");
    localStorage.removeItem("soukpilot_username");
    localStorage.removeItem("soukpilot_business");
    navigate("/login", { replace: true });
  }
  return (
    <button onClick={logout} title="Sign out" style={S.logoutBtn}>
      <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M6 2H3a1 1 0 00-1 1v10a1 1 0 001 1h3" />
        <path d="M11 11l3-3-3-3" />
        <line x1="14" y1="8" x2="6" y2="8" />
      </svg>
    </button>
  );
}

function SidebarFooter() {
  const business = localStorage.getItem("soukpilot_business");
  const username = localStorage.getItem("soukpilot_username");
  const label = business || username || "My Business";
  return (
    <div style={S.sidebarFooter}>
      <span style={S.footerDot} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 11, color: "rgba(255,255,255,0.55)", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {label}
        </div>
        <div style={{ fontSize: 10, color: "rgba(255,255,255,0.22)", marginTop: 1 }}>v0.1.0</div>
      </div>
      <LogoutButton />
    </div>
  );
}

// ── Shell layout (sidebar + topbar + main) ──────────────────────────────────

function MainLayout() {
  const isMobile = useIsMobile();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const toggle = () => setOpen(v => !v);
  const close = () => setOpen(false);

  useEffect(() => { setOpen(false); }, [location.pathname]);

  const sidebarStyle: React.CSSProperties = isMobile
    ? {
        ...S.sidebar,
        position: "fixed",
        top: 0,
        left: 0,
        height: "100vh",
        zIndex: 200,
        transform: open ? "translateX(0)" : "translateX(-228px)",
        transition: "transform 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
        boxShadow: open ? "4px 0 40px rgba(0,0,0,0.6)" : "none",
      }
    : S.sidebar;

  return (
    <MobileNavCtx.Provider value={{ isMobile, open, toggle, close }}>
    <div style={S.shell}>
      <div style={S.blob1} aria-hidden="true" />
      <div style={S.blob2} aria-hidden="true" />
      <div style={S.blob3} aria-hidden="true" />

      {isMobile && open && (
        <div
          onClick={close}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 199 }}
        />
      )}

      <nav style={sidebarStyle}>
        <div style={S.logo}>
          <svg width="162" height="40" viewBox="0 0 162 40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M4 36 L4 19 Q4 4 18 4 Q32 4 32 19 L32 36" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" fill="none"/>
            <path d="M9 36 L9 20 Q9 10 18 10 Q27 10 27 20 L27 36" stroke="#a5b4fc" strokeWidth="1" strokeLinecap="round" fill="none" opacity="0.4"/>
            <line x1="1" y1="36" x2="35" y2="36" stroke="#818cf8" strokeWidth="2" strokeLinecap="round"/>
            <text x="46" y="18" fontFamily="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" fontSize="11" fontWeight="300" fill="rgba(255,255,255,0.28)" letterSpacing="2.5">SOUK</text>
            <text x="46" y="34" fontFamily="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" fontSize="13" fontWeight="800" fill="rgba(255,255,255,0.92)" letterSpacing="2.5">PILOT</text>
            <text x="126" y="34" fontFamily="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" fontSize="9" fontWeight="700" fill="#818cf8" letterSpacing="1">AI</text>
          </svg>
        </div>

        <ul style={S.navList}>
          {NAV_GROUPS.map((group, gi) => (
            <li key={gi}>
              {group.label && <div style={S.navGroupLabel}>{group.label}</div>}
              <ul style={{ listStyle: "none" }}>
                {group.items.map(({ to, label, icon }) => (
                  <li key={to}>
                    <NavLink
                      to={to}
                      end={to === "/"}
                      style={({ isActive }) => ({ ...S.navLink, ...(isActive ? S.navLinkActive : {}) })}
                    >
                      <span style={S.navIcon}>{icon}</span>
                      {label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>

        <SidebarFooter />
      </nav>

      <div style={S.contentWrapper}>
        <Topbar />
        <main style={{ ...S.main, padding: isMobile ? "16px 14px 32px" : "28px 36px 40px" }}>
          <Routes>
            <Route path="/"               element={<Dashboard />} />
            <Route path="/invoices"       element={<InvoiceUpload />} />
            <Route path="/orders"         element={<Orders />} />
            <Route path="/inventory"      element={<Inventory />} />
            <Route path="/pricing"        element={<PricingAdvisor />} />
            <Route path="/qa"             element={<BusinessQA />} />
            <Route path="/reports"        element={<Reports />} />
            <Route path="/voice"          element={<VoiceAssistant />} />
            <Route path="/agent"          element={<AgentChat />} />
            <Route path="/widget-settings" element={<WidgetSettings />} />
          </Routes>
        </main>
      </div>
    </div>
    </MobileNavCtx.Provider>
  );
}

// ── Auth guard ───────────────────────────────────────────────────────────────

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("soukpilot_token");
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public standalone routes */}
        <Route path="/login"       element={<Login />} />
        <Route path="/register"    element={<Register />} />
        <Route path="/widget"      element={<WidgetChat />} />
        <Route path="/superadmin"  element={<SuperAdmin />} />
        {/* Everything else requires auth and gets the full shell */}
        <Route path="/*" element={<RequireAuth><MainLayout /></RequireAuth>} />
      </Routes>
    </BrowserRouter>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const S: Record<string, React.CSSProperties> = {

  // Shell layout
  shell: {
    display: "flex",
    height: "100vh",
    overflow: "hidden",
    position: "relative",
    isolation: "isolate",
  },
  contentWrapper: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    minWidth: 0,
  },
  main: {
    flex: 1,
    overflowY: "auto",
    padding: "28px 36px 40px",
    maxWidth: 1280,
    width: "100%",
    position: "relative",
    zIndex: 1,
  },

  // Aurora blobs
  blob1: {
    position: "fixed",
    top: "-18vh",
    left: "22%",
    width: "58vh",
    height: "58vh",
    background: "radial-gradient(circle, rgba(99,102,241,0.14) 0%, transparent 65%)",
    pointerEvents: "none",
    zIndex: 0,
    animation: "aurora-drift 18s ease-in-out infinite",
  },
  blob2: {
    position: "fixed",
    bottom: "-12vh",
    right: "6%",
    width: "52vh",
    height: "52vh",
    background: "radial-gradient(circle, rgba(168,85,247,0.12) 0%, transparent 65%)",
    pointerEvents: "none",
    zIndex: 0,
    animation: "aurora-drift 24s ease-in-out infinite reverse",
  },
  blob3: {
    position: "fixed",
    top: "38%",
    left: "-6%",
    width: "44vh",
    height: "44vh",
    background: "radial-gradient(circle, rgba(14,165,233,0.08) 0%, transparent 65%)",
    pointerEvents: "none",
    zIndex: 0,
    animation: "aurora-drift 20s ease-in-out infinite 6s",
  },

  // Sidebar
  sidebar: {
    width: 228,
    background: "rgba(255, 255, 255, 0.03)",
    backdropFilter: "blur(20px)",
    WebkitBackdropFilter: "blur(20px)",
    borderRight: "1px solid rgba(255, 255, 255, 0.07)",
    display: "flex",
    flexDirection: "column",
    padding: "24px 0 16px",
    flexShrink: 0,
    height: "100%",
    overflowY: "auto",
    zIndex: 10,
  },
  logo: {
    display: "flex",
    alignItems: "center",
    padding: "4px 20px 24px",
    borderBottom: "1px solid rgba(255, 255, 255, 0.07)",
    marginBottom: 8,
  },
  navList: {
    listStyle: "none",
    flex: 1,
    paddingBottom: 8,
  },
  navGroupLabel: {
    fontSize: 10,
    fontWeight: 700,
    color: "rgba(255, 255, 255, 0.2)",
    textTransform: "uppercase",
    letterSpacing: "1.2px",
    padding: "14px 20px 5px",
  },
  navLink: {
    display: "flex",
    alignItems: "center",
    gap: 9,
    padding: "8px 14px 8px 17px",
    color: "rgba(255, 255, 255, 0.36)",
    fontSize: 13,
    transition: "all 0.15s ease",
    borderLeft: "2px solid transparent",
    borderRadius: "0 8px 8px 0",
    margin: "0 8px 1px 0",
  },
  navLinkActive: {
    color: "rgba(255, 255, 255, 0.92)",
    background: "rgba(99, 102, 241, 0.14)",
    borderLeftColor: "#818cf8",
    boxShadow: "inset 0 0 0 1px rgba(99,102,241,0.2)",
    fontWeight: 500,
  },
  navIcon: {
    width: 18,
    height: 18,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
    opacity: 0.85,
  },
  sidebarFooter: {
    padding: "12px 20px",
    display: "flex",
    alignItems: "center",
    gap: 8,
    color: "rgba(255, 255, 255, 0.26)",
    fontSize: 11,
    borderTop: "1px solid rgba(255, 255, 255, 0.06)",
  },
  footerDot: {
    width: 7,
    height: 7,
    borderRadius: "50%",
    background: "#34d399",
    flexShrink: 0,
    display: "inline-block",
  },
  hamburgerBtn: {
    background: "transparent",
    border: "none",
    color: "rgba(255,255,255,0.55)",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "4px",
    flexShrink: 0,
    borderRadius: 6,
  },
  logoutBtn: {
    background: "transparent",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 6,
    color: "rgba(255,255,255,0.35)",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "4px 6px",
    flexShrink: 0,
    transition: "color 0.15s, border-color 0.15s",
  },

  // Topbar
  topbar: {
    flexShrink: 0,
    height: 52,
    background: "rgba(6, 8, 24, 0.88)",
    backdropFilter: "blur(24px)",
    WebkitBackdropFilter: "blur(24px)",
    borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 36px",
    zIndex: 9,
  },
  topbarLeft: {
    display: "flex",
    alignItems: "center",
  },
  crumbGroup: {
    color: "rgba(255, 255, 255, 0.28)",
    fontSize: 12.5,
  },
  crumbSep: {
    color: "rgba(255, 255, 255, 0.16)",
    fontSize: 13,
    margin: "0 8px",
  },
  crumbPage: {
    color: "rgba(255, 255, 255, 0.62)",
    fontSize: 12.5,
    fontWeight: 500,
    letterSpacing: "0.1px",
  },
  topbarRight: {
    display: "flex",
    alignItems: "center",
    gap: 14,
  },
  topbarDate: {
    color: "rgba(255, 255, 255, 0.28)",
    fontSize: 12,
  },
  topbarTime: {
    color: "rgba(255, 255, 255, 0.42)",
    fontSize: 12,
    letterSpacing: "0.5px",
  },
  liveChip: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    background: "rgba(52, 211, 153, 0.07)",
    border: "1px solid rgba(52, 211, 153, 0.2)",
    borderRadius: 100,
    padding: "3px 10px 3px 8px",
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: "50%",
    background: "#34d399",
    display: "inline-block",
    animation: "live-pulse 2.5s ease-in-out infinite",
  },
  liveLabel: {
    color: "#34d399",
    fontSize: 10.5,
    fontWeight: 600,
    letterSpacing: "0.6px",
    textTransform: "uppercase",
  },
};
