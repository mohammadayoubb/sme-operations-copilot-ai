import { useState } from "react";
import PageShell from "../components/PageShell";

export default function VoiceAssistant() {
  const [recording, setRecording] = useState(false);

  return (
    <PageShell title="Voice Assistant" subtitle="Speak a sale, order, or command — the AI transcribes, understands, and acts on it">
      <div style={styles.card}>
        <div style={styles.micWrapper}>
          <button
            style={{ ...styles.micBtn, ...(recording ? styles.micBtnActive : {}) }}
            onClick={() => setRecording((r) => !r)}
          >
            <span style={styles.micIcon}>🎙</span>
          </button>
          <p style={styles.micStatus}>
            {recording ? "Recording… click to stop" : "Click to start recording"}
          </p>
        </div>

        <div style={styles.divider}>or</div>

        <div>
          <label style={styles.label}>Upload an audio file</label>
          <input type="file" accept="audio/*" style={styles.fileInput} />
        </div>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Example commands you can say</h3>
        <div style={styles.exampleGrid}>
          {[
            "Add sale: 3 Pepsi and 2 chips",
            "How many Nutella do I have left?",
            "Record delivery of 24 bottles of water",
            "What were my best sellers today?",
          ].map((cmd) => (
            <div key={cmd} style={styles.exampleCard}>
              <span style={styles.exampleIcon}>🎤</span>
              <span style={styles.exampleText}>"{cmd}"</span>
            </div>
          ))}
        </div>
      </div>

      <div style={styles.emptyState}>
        Transcription and AI response will appear here after recording.
      </div>
    </PageShell>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 32, marginBottom: 28, textAlign: "center" },
  micWrapper: { display: "flex", flexDirection: "column", alignItems: "center", gap: 16, marginBottom: 24 },
  micBtn: {
    width: 80, height: 80, borderRadius: "50%",
    background: "var(--surface2)", border: "2px solid var(--border)",
    display: "flex", alignItems: "center", justifyContent: "center",
    cursor: "pointer", transition: "all 0.2s",
  },
  micBtnActive: { background: "#ef444422", borderColor: "#ef4444", boxShadow: "0 0 0 8px #ef444422" },
  micIcon: { fontSize: 32 },
  micStatus: { color: "var(--text-muted)", fontSize: 13 },
  divider: { color: "var(--text-muted)", margin: "16px 0", fontSize: 13 },
  label: { display: "block", fontSize: 13, color: "var(--text-muted)", marginBottom: 8 },
  fileInput: { color: "var(--text)" },
  section: { marginBottom: 28 },
  sectionTitle: { fontWeight: 600, marginBottom: 14, fontSize: 15 },
  exampleGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 },
  exampleCard: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "14px 16px", display: "flex", gap: 10, alignItems: "flex-start" },
  exampleIcon: { fontSize: 16 },
  exampleText: { color: "var(--text-muted)", fontSize: 13, fontStyle: "italic" },
  emptyState: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 24, color: "var(--text-muted)", textAlign: "center" },
};
