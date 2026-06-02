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
  header: { marginBottom: 28 },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 6 },
  subtitle: { color: "var(--text-muted)", fontSize: 14, lineHeight: 1.5 },
};
