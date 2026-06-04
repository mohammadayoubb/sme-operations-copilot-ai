import { type ReactNode } from "react";

interface Props {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
}

export default function PageShell({ title, subtitle, actions, children }: Props) {
  return (
    <div>
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <h1 style={styles.title}>{title}</h1>
          {subtitle && <p style={styles.subtitle}>{subtitle}</p>}
        </div>
        {actions && <div style={styles.headerActions}>{actions}</div>}
      </div>
      {children}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  header: {
    marginBottom: 32,
    paddingBottom: 24,
    borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 16,
  },
  headerLeft: {
    flex: 1,
    minWidth: 0,
  },
  title: {
    fontSize: 22,
    fontWeight: 700,
    marginBottom: 5,
    letterSpacing: "-0.4px",
    color: "rgba(255, 255, 255, 0.95)",
  },
  subtitle: {
    color: "rgba(255, 255, 255, 0.36)",
    fontSize: 13,
    lineHeight: 1.55,
  },
  headerActions: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    flexShrink: 0,
    paddingTop: 2,
  },
};
