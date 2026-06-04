import { type ReactNode } from "react";

interface Props {
  title: string;
  subtitle?: string;
  children: ReactNode;
}

export default function PageShell({ title, subtitle, children }: Props) {
  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.title}>{title}</h1>
        {subtitle && <p style={styles.subtitle}>{subtitle}</p>}
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
  },
  title: {
    fontSize: 24,
    fontWeight: 700,
    marginBottom: 6,
    letterSpacing: "-0.5px",
    color: "rgba(255, 255, 255, 0.95)",
  },
  subtitle: {
    color: "rgba(255, 255, 255, 0.38)",
    fontSize: 13.5,
    lineHeight: 1.5,
  },
};
