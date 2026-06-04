import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import InvoiceUpload from "./pages/InvoiceUpload";
import Orders from "./pages/Orders";
import Inventory from "./pages/Inventory";
import PricingAdvisor from "./pages/PricingAdvisor";
import BusinessQA from "./pages/BusinessQA";
import Reports from "./pages/Reports";
import VoiceAssistant from "./pages/VoiceAssistant";
import AgentChat from "./pages/AgentChat";

const NAV = [
  { to: "/",          label: "Dashboard",      icon: "▦" },
  { to: "/invoices",  label: "Invoices",        icon: "📄" },
  { to: "/orders",    label: "Orders",          icon: "🛍" },
  { to: "/inventory", label: "Inventory",       icon: "📦" },
  { to: "/pricing",   label: "Pricing Advisor", icon: "💰" },
  { to: "/qa",        label: "Business Q&A",    icon: "💬" },
  { to: "/reports",   label: "Reports",         icon: "📊" },
  { to: "/voice",     label: "Voice",           icon: "🎙" },
  { to: "/agent",     label: "AI Agent",        icon: "🤖" },
];

export default function App() {
  return (
    <BrowserRouter>
      <div style={styles.shell}>

        {/* ── Aurora background blobs ── */}
        <div style={styles.blob1} aria-hidden="true" />
        <div style={styles.blob2} aria-hidden="true" />
        <div style={styles.blob3} aria-hidden="true" />

        {/* ── Sidebar ── */}
        <nav style={styles.sidebar}>
          <div style={styles.logo}>
            <svg width="162" height="40" viewBox="0 0 162 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M4 36 L4 19 Q4 4 18 4 Q32 4 32 19 L32 36" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" fill="none"/>
              <path d="M9 36 L9 20 Q9 10 18 10 Q27 10 27 20 L27 36" stroke="#a5b4fc" strokeWidth="1" strokeLinecap="round" fill="none" opacity="0.4"/>
              <line x1="1" y1="36" x2="35" y2="36" stroke="#818cf8" strokeWidth="2" strokeLinecap="round"/>
              <text x="46" y="18" fontFamily="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" fontSize="11" fontWeight="300" fill="rgba(255,255,255,0.28)" letterSpacing="2.5">SOUK</text>
              <text x="46" y="34" fontFamily="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" fontSize="13" fontWeight="800" fill="rgba(255,255,255,0.92)" letterSpacing="2.5">PILOT</text>
              <text x="126" y="34" fontFamily="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" fontSize="9" fontWeight="700" fill="#818cf8" letterSpacing="1">AI</text>
            </svg>
          </div>

          <ul style={styles.navList}>
            {NAV.map(({ to, label, icon }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={to === "/"}
                  style={({ isActive }) => ({
                    ...styles.navLink,
                    ...(isActive ? styles.navLinkActive : {}),
                  })}
                >
                  <span style={styles.navIcon}>{icon}</span>
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>

          <div style={styles.sidebarFooter}>v0.1.0 · MVP</div>
        </nav>

        {/* ── Main content ── */}
        <main style={styles.main}>
          <Routes>
            <Route path="/"          element={<Dashboard />} />
            <Route path="/invoices"  element={<InvoiceUpload />} />
            <Route path="/orders"    element={<Orders />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/pricing"   element={<PricingAdvisor />} />
            <Route path="/qa"        element={<BusinessQA />} />
            <Route path="/reports"   element={<Reports />} />
            <Route path="/voice"     element={<VoiceAssistant />} />
            <Route path="/agent"     element={<AgentChat />} />
          </Routes>
        </main>

      </div>
    </BrowserRouter>
  );
}

const styles: Record<string, React.CSSProperties> = {
  shell: {
    display: "flex",
    minHeight: "100vh",
    position: "relative",
    isolation: "isolate",
  },

  /* ── Aurora blobs ── */
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

  /* ── Sidebar ── */
  sidebar: {
    width: 220,
    background: "rgba(255, 255, 255, 0.03)",
    backdropFilter: "blur(20px)",
    WebkitBackdropFilter: "blur(20px)",
    borderRight: "1px solid rgba(255, 255, 255, 0.07)",
    display: "flex",
    flexDirection: "column",
    padding: "24px 0 16px",
    flexShrink: 0,
    position: "sticky",
    top: 0,
    height: "100vh",
    overflowY: "auto",
    zIndex: 10,
  },
  logo: {
    display: "flex",
    alignItems: "center",
    padding: "4px 20px 28px",
    borderBottom: "1px solid rgba(255, 255, 255, 0.07)",
    marginBottom: 16,
  },
  navList: { listStyle: "none", flex: 1 },
  navLink: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "9px 14px 9px 17px",
    color: "rgba(255, 255, 255, 0.32)",
    fontSize: 13.5,
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
  },
  navIcon: { fontSize: 15, width: 20, textAlign: "center" },
  sidebarFooter: {
    padding: "12px 20px",
    color: "rgba(255, 255, 255, 0.18)",
    fontSize: 11,
    borderTop: "1px solid rgba(255, 255, 255, 0.06)",
  },

  /* ── Main ── */
  main: {
    flex: 1,
    padding: "32px 36px",
    overflowY: "auto",
    maxWidth: 1100,
    position: "relative",
    zIndex: 1,
  },
};
