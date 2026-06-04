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
        <nav style={styles.sidebar}>
          <div style={styles.logo}>
            <svg width="162" height="40" viewBox="0 0 162 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              {/* arch */}
              <path d="M4 36 L4 19 Q4 4 18 4 Q32 4 32 19 L32 36" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" fill="none"/>
              <path d="M9 36 L9 20 Q9 10 18 10 Q27 10 27 20 L27 36" stroke="#818cf8" strokeWidth="1" strokeLinecap="round" fill="none" opacity="0.45"/>
              <line x1="1" y1="36" x2="35" y2="36" stroke="#6366f1" strokeWidth="2" strokeLinecap="round"/>
              {/* SOUK */}
              <text x="46" y="18" fontFamily="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" fontSize="11" fontWeight="300" fill="#64748b" letterSpacing="2.5">SOUK</text>
              {/* PILOT */}
              <text x="46" y="34" fontFamily="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" fontSize="13" fontWeight="800" fill="#e2e8f0" letterSpacing="2.5">PILOT</text>
              {/* AI accent */}
              <text x="126" y="34" fontFamily="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" fontSize="9" fontWeight="700" fill="#6366f1" letterSpacing="1">AI</text>
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
  },
  sidebar: {
    width: 220,
    background: "var(--surface)",
    borderRight: "1px solid var(--border)",
    display: "flex",
    flexDirection: "column",
    padding: "24px 0 16px",
    flexShrink: 0,
    position: "sticky",
    top: 0,
    height: "100vh",
    overflowY: "auto",
  },
  logo: {
    display: "flex",
    alignItems: "center",
    padding: "4px 20px 28px",
    borderBottom: "1px solid var(--border)",
    marginBottom: 16,
  },
  navList: { listStyle: "none", flex: 1 },
  navLink: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "9px 20px",
    color: "var(--text-muted)",
    borderRadius: 0,
    fontSize: 13.5,
    transition: "all 0.15s",
    borderLeft: "3px solid transparent",
  },
  navLinkActive: {
    color: "var(--text)",
    background: "var(--surface2)",
    borderLeftColor: "var(--accent)",
  },
  navIcon: { fontSize: 15, width: 20, textAlign: "center" },
  main: {
    flex: 1,
    padding: "32px 36px",
    overflowY: "auto",
    maxWidth: 1100,
  },
  sidebarFooter: {
    padding: "12px 20px",
    color: "var(--text-muted)",
    fontSize: 11,
    borderTop: "1px solid var(--border)",
  },
};
