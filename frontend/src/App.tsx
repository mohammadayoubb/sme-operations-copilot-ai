import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import InvoiceUpload from "./pages/InvoiceUpload";
import Orders from "./pages/Orders";
import Inventory from "./pages/Inventory";
import PricingAdvisor from "./pages/PricingAdvisor";
import BusinessQA from "./pages/BusinessQA";
import Reports from "./pages/Reports";
import VoiceAssistant from "./pages/VoiceAssistant";

const NAV = [
  { to: "/",          label: "Dashboard",      icon: "▦" },
  { to: "/invoices",  label: "Invoices",        icon: "📄" },
  { to: "/orders",    label: "Orders",          icon: "🛍" },
  { to: "/inventory", label: "Inventory",       icon: "📦" },
  { to: "/pricing",   label: "Pricing Advisor", icon: "💰" },
  { to: "/qa",        label: "Business Q&A",    icon: "💬" },
  { to: "/reports",   label: "Reports",         icon: "📊" },
  { to: "/voice",     label: "Voice",           icon: "🎙" },
];

export default function App() {
  return (
    <BrowserRouter>
      <div style={styles.shell}>
        <nav style={styles.sidebar}>
          <div style={styles.logo}>
            <span style={styles.logoIcon}>◈</span>
            <span style={styles.logoText}>SoukPilot AI</span>
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
    gap: 10,
    padding: "0 20px 28px",
    borderBottom: "1px solid var(--border)",
    marginBottom: 16,
  },
  logoIcon: { fontSize: 22, color: "var(--accent)" },
  logoText: { fontWeight: 700, fontSize: 15, letterSpacing: "-0.3px" },
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
