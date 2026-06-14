import { useEffect, useRef } from "react";
import PageShell from "../components/PageShell";

const W = 800, H = 320;
const GY = 252;       // ground top Y
const GRAVITY = 0.52;
const JUMP_FORCE = -11.5;
const RX = 90;        // runner fixed X
const RW = 22, RH = 38;

type GameState = "idle" | "playing" | "dead";
type ObsType = "invoice" | "spike" | "box";

interface Obs      { x: number; y: number; w: number; h: number; type: ObsType }
interface Particle { x: number; y: number; vx: number; vy: number; life: number; maxLife: number; color: string; r: number }
interface Star     { x: number; y: number; r: number; speed: number }
interface BgStall  { x: number; color: string }

export default function SoukRunner() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current!;
    const ctx    = canvas.getContext("2d")!;

    // ── mutable game state (closure, no React state to avoid stutter) ──
    let state: GameState = "idle";
    let score  = 0;
    let best   = parseInt(localStorage.getItem("soukpilot_runner_best") ?? "0");
    let speed  = 4.5;
    let tick   = 0;
    let jumpCount = 0;
    let shakeTimer = 0;

    // runner physics
    let ry = GY - RH;
    let rvy = 0;
    let onGround = true;
    let legPhase = 0;

    // entities
    let obstacles: Obs[]      = [];
    let particles: Particle[] = [];

    // background
    const stars: Star[] = Array.from({ length: 45 }, () => ({
      x: Math.random() * W,
      y: Math.random() * (GY - 30),
      r: Math.random() * 1.5 + 0.4,
      speed: 0.25 + Math.random() * 0.5,
    }));
    const bgStalls: BgStall[] = [
      { x: 580,  color: "#818cf8" },
      { x: 950,  color: "#34d399" },
      { x: 1320, color: "#fb923c" },
      { x: 1700, color: "#a78bfa" },
    ];

    // ── input ──────────────────────────────────────────────────────────
    function jump() {
      if (state === "idle" || state === "dead") { restart(); return; }
      if (jumpCount < 2) {
        rvy = jumpCount === 0 ? JUMP_FORCE : JUMP_FORCE * 0.80;
        onGround = false;
        jumpCount++;
        spawnJumpDust();
      }
    }

    const onKey   = (e: KeyboardEvent)  => { if (e.code === "Space" || e.code === "ArrowUp") { e.preventDefault(); jump(); } };
    const onClick = ()                  => jump();
    const onTouch = (e: TouchEvent)     => { e.preventDefault(); jump(); };

    canvas.addEventListener("click",      onClick);
    canvas.addEventListener("touchstart", onTouch, { passive: false });
    window.addEventListener("keydown",    onKey);

    // ── game control ───────────────────────────────────────────────────
    function restart() {
      state = "playing";
      score = 0; speed = 4.5; tick = 0; jumpCount = 0; shakeTimer = 0;
      ry = GY - RH; rvy = 0; onGround = true;
      obstacles = []; particles = [];
    }

    function die() {
      state = "dead";
      if (score > best) {
        best = score;
        localStorage.setItem("soukpilot_runner_best", String(best));
      }
      shakeTimer = 14;
      for (let i = 0; i < 22; i++) {
        particles.push({
          x: RX + RW / 2, y: ry + RH / 2,
          vx: (Math.random() - 0.5) * 9,
          vy: (Math.random() - 0.85) * 8,
          life: 38, maxLife: 38,
          color: ["#f87171","#FCD34D","#818cf8","#F5C09A","#a78bfa"][i % 5],
          r: 2 + Math.random() * 4,
        });
      }
    }

    function spawnJumpDust() {
      for (let i = 0; i < 7; i++) {
        particles.push({
          x: RX + RW / 2, y: GY,
          vx: (Math.random() - 0.5) * 3.5,
          vy: Math.random() * 2 + 0.5,
          life: 18, maxLife: 18,
          color: "#5B21B6", r: 2 + Math.random() * 2,
        });
      }
    }

    function spawnObstacle() {
      const roll = Math.random();
      let type: ObsType, w: number, h: number;
      if      (roll < 0.38) { type = "invoice"; w = 20; h = 42; }
      else if (roll < 0.68) { type = "spike";   w = 24; h = 38; }
      else                  { type = "box";      w = 32; h = 26; }
      obstacles.push({ x: W + 20, y: GY - h, w, h, type });
    }

    // ── drawing helpers ────────────────────────────────────────────────
    function drawBgStall(s: BgStall) {
      const w = 78, h = 52;
      ctx.fillStyle = "rgba(255,255,255,0.025)";
      ctx.beginPath(); ctx.roundRect(s.x, GY - h, w, h, 3); ctx.fill();
      ctx.fillStyle = s.color;
      ctx.globalAlpha = 0.28;
      ctx.beginPath();
      ctx.moveTo(s.x - 4, GY - h);
      ctx.lineTo(s.x + w + 4, GY - h);
      ctx.lineTo(s.x + w, GY - h + 13);
      ctx.lineTo(s.x, GY - h + 13);
      ctx.closePath(); ctx.fill();
      ctx.globalAlpha = 1;
    }

    function drawObstacle(o: Obs) {
      if (o.type === "invoice") {
        ctx.fillStyle = "#818cf8";
        ctx.beginPath(); ctx.roundRect(o.x, o.y, o.w, o.h, 3); ctx.fill();
        ctx.fillStyle = "rgba(255,255,255,0.22)";
        for (let dy = 8; dy < o.h - 4; dy += 7) ctx.fillRect(o.x + 4, o.y + dy, o.w - 8, 2);
        ctx.fillStyle = "rgba(255,255,255,0.75)";
        ctx.font = "bold 6px Inter,sans-serif"; ctx.textAlign = "center";
        ctx.fillText("INV", o.x + o.w / 2, o.y + 7);
      } else if (o.type === "spike") {
        ctx.fillStyle = "#f87171";
        ctx.beginPath();
        ctx.moveTo(o.x + o.w / 2, o.y);
        ctx.lineTo(o.x, o.y + o.h);
        ctx.lineTo(o.x + o.w, o.y + o.h);
        ctx.closePath(); ctx.fill();
        ctx.fillStyle = "rgba(255,255,255,0.55)";
        ctx.font = "bold 7px Inter,sans-serif"; ctx.textAlign = "center";
        ctx.fillText("$↑", o.x + o.w / 2, o.y + o.h - 4);
      } else {
        ctx.fillStyle = "#fb923c";
        ctx.beginPath(); ctx.roundRect(o.x, o.y, o.w, o.h, 4); ctx.fill();
        ctx.fillStyle = "#92400E";
        ctx.beginPath(); ctx.roundRect(o.x + 2, o.y + 2, o.w - 4, 7, 2); ctx.fill();
        ctx.fillStyle = "rgba(255,255,255,0.65)";
        ctx.font = "bold 6px Inter,sans-serif"; ctx.textAlign = "center";
        ctx.fillText("BOX", o.x + o.w / 2, o.y + o.h / 2 + 3);
      }
    }

    function drawRunner(isDead: boolean) {
      const lp   = legPhase;
      const lSwing = Math.sin(lp) * 0.42;

      // Legs
      ctx.strokeStyle = "#5B21B6"; ctx.lineWidth = 5; ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(RX + 8,  ry + RH - 2); ctx.lineTo(RX + 8  + Math.sin(lp)  * 10, GY); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(RX + 14, ry + RH - 2); ctx.lineTo(RX + 14 - Math.sin(lp)  * 10, GY); ctx.stroke();

      // Body
      ctx.fillStyle = "#7C3AED";
      ctx.beginPath(); ctx.roundRect(RX, ry + 10, RW, RH - 10, 4); ctx.fill();

      // Collar
      ctx.fillStyle = "#5B21B6";
      ctx.beginPath();
      ctx.moveTo(RX + 6, ry + 10); ctx.lineTo(RX + RW / 2, ry + 18); ctx.lineTo(RX + RW - 6, ry + 10);
      ctx.fill();

      // Arms (swing opposite to legs)
      ctx.strokeStyle = "#6D28D9"; ctx.lineWidth = 5;
      ctx.beginPath(); ctx.moveTo(RX + 2,        ry + 15); ctx.lineTo(RX - 7   + Math.sin(lp)  * 7, ry + 26); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(RX + RW - 2,   ry + 15); ctx.lineTo(RX + RW + 7 - Math.sin(lp)  * 7, ry + 26); ctx.stroke();

      // Head
      ctx.fillStyle = "#F5C09A";
      ctx.beginPath(); ctx.arc(RX + RW / 2, ry + 6, 10, 0, Math.PI * 2); ctx.fill();

      // Fez cylinder
      ctx.fillStyle = "#DC2626";
      ctx.beginPath(); ctx.roundRect(RX + 3, ry - 6, RW - 6, 9, [3, 3, 0, 0]); ctx.fill();
      // Fez brim
      ctx.fillStyle = "#991B1B";
      ctx.beginPath(); ctx.ellipse(RX + RW / 2, ry + 3, RW / 2 - 1, 4, 0, 0, Math.PI * 2); ctx.fill();
      // Fez top
      ctx.fillStyle = "#EF4444";
      ctx.beginPath(); ctx.ellipse(RX + RW / 2, ry - 6, RW / 2 - 5, 3, 0, 0, Math.PI * 2); ctx.fill();
      // Tassel
      ctx.strokeStyle = "#D97706"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(RX + RW - 4, ry - 6); ctx.lineTo(RX + RW + 3, ry - 13 + Math.sin(lp) * 2); ctx.stroke();
      ctx.fillStyle = "#D97706";
      ctx.beginPath(); ctx.arc(RX + RW + 3, ry - 14 + Math.sin(lp) * 2, 2.5, 0, Math.PI * 2); ctx.fill();

      // Eyes
      if (isDead) {
        // X eyes
        ctx.strokeStyle = "#1A0A00"; ctx.lineWidth = 1.5; ctx.lineCap = "round";
        [RX + 7, RX + 15].forEach(ex => {
          ctx.beginPath(); ctx.moveTo(ex - 2, ry + 2); ctx.lineTo(ex + 2, ry + 6); ctx.stroke();
          ctx.beginPath(); ctx.moveTo(ex + 2, ry + 2); ctx.lineTo(ex - 2, ry + 6); ctx.stroke();
        });
      } else {
        ctx.fillStyle = "#1A0A00";
        ctx.beginPath(); ctx.arc(RX + 7,  ry + 4, 2, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.arc(RX + 15, ry + 4, 2, 0, Math.PI * 2); ctx.fill();
        // Shine dots
        ctx.fillStyle = "rgba(255,255,255,0.7)";
        ctx.beginPath(); ctx.arc(RX + 8,  ry + 3, 0.8, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.arc(RX + 16, ry + 3, 0.8, 0, Math.PI * 2); ctx.fill();
        // Mouth (small smile)
        ctx.strokeStyle = "#B05030"; ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.arc(RX + RW / 2, ry + 7, 3.5, 0.2, Math.PI - 0.2); ctx.stroke();
      }

      // Running dust trail when on ground
      if (state === "playing" && onGround && tick % 5 === 0) {
        particles.push({
          x: RX + 3, y: GY,
          vx: -(Math.random() * 1.5 + 0.5),
          vy: -(Math.random() * 0.8),
          life: 14, maxLife: 14,
          color: "#1a1030", r: 2 + Math.random() * 2,
        });
      }
    }

    function drawHUD() {
      // Score
      ctx.textAlign = "right";
      ctx.fillStyle = "rgba(255,255,255,0.88)";
      ctx.font = "bold 22px Inter,system-ui,sans-serif";
      ctx.fillText(score + "m", W - 20, 34);
      ctx.fillStyle = "rgba(255,255,255,0.32)";
      ctx.font = "12px Inter,system-ui,sans-serif";
      ctx.fillText("best " + best + "m", W - 20, 54);

      // Double-jump pips
      if (state === "playing" && !onGround) {
        for (let i = 0; i < 2; i++) {
          ctx.beginPath();
          ctx.arc(22 + i * 16, 22, 5, 0, Math.PI * 2);
          ctx.fillStyle = i < (2 - jumpCount) ? "#818cf8" : "rgba(255,255,255,0.1)";
          ctx.fill();
        }
        ctx.fillStyle = "rgba(255,255,255,0.25)";
        ctx.font = "9px Inter,sans-serif"; ctx.textAlign = "left";
        ctx.fillText("jumps", 52, 26);
      }
    }

    function drawIdleScreen() {
      ctx.fillStyle = "rgba(6,8,24,0.52)";
      ctx.fillRect(0, 0, W, H);
      ctx.textAlign = "center";
      ctx.fillStyle = "rgba(255,255,255,0.9)";
      ctx.font = "bold 30px Inter,system-ui,sans-serif";
      ctx.fillText("Souk Runner", W / 2, H / 2 - 30);
      ctx.fillStyle = "rgba(255,255,255,0.42)";
      ctx.font = "14px Inter,system-ui,sans-serif";
      ctx.fillText("Click · tap · Space to jump     Double jump allowed", W / 2, H / 2 + 2);
      ctx.fillStyle = "rgba(129,140,248,0.8)";
      ctx.font = "13px Inter,system-ui,sans-serif";
      ctx.fillText("Dodge invoices  ▲ price spikes  and boxes", W / 2, H / 2 + 28);
      if (best > 0) {
        ctx.fillStyle = "rgba(255,255,255,0.28)";
        ctx.font = "12px Inter,system-ui,sans-serif";
        ctx.fillText("Your best: " + best + "m", W / 2, H / 2 + 54);
      }
    }

    function drawDeadScreen() {
      const isNewBest = score === best && score > 0;
      ctx.fillStyle = "rgba(6,8,24,0.68)";
      ctx.fillRect(0, 0, W, H);
      ctx.textAlign = "center";
      ctx.fillStyle = "rgba(255,255,255,0.92)";
      ctx.font = "bold 28px Inter,system-ui,sans-serif";
      ctx.fillText("Game over!", W / 2, H / 2 - 26);
      ctx.fillStyle = isNewBest ? "#FCD34D" : "rgba(255,255,255,0.55)";
      ctx.font = "15px Inter,system-ui,sans-serif";
      ctx.fillText(score + "m" + (isNewBest ? "   ★ New best!" : ""), W / 2, H / 2 + 4);
      ctx.fillStyle = "#818cf8";
      ctx.font = "13px Inter,system-ui,sans-serif";
      ctx.fillText("Click or Space to play again", W / 2, H / 2 + 34);
    }

    // ── main loop ──────────────────────────────────────────────────────
    let raf: number;

    function loop() {
      tick++;

      // Screen shake offset
      const sx = shakeTimer > 0 ? (Math.random() - 0.5) * 7 : 0;
      const sy = shakeTimer > 0 ? (Math.random() - 0.5) * 5 : 0;
      if (shakeTimer > 0) shakeTimer--;

      ctx.save();
      ctx.translate(sx, sy);
      ctx.clearRect(-12, -12, W + 24, H + 24);

      // ── Sky ──
      ctx.fillStyle = "#060818";
      ctx.fillRect(-12, -12, W + 24, H + 24);

      // ── Stars ──
      stars.forEach(s => {
        if (state === "playing") { s.x -= s.speed; if (s.x < -2) s.x = W + 2; }
        ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${0.18 + s.r * 0.18})`;
        ctx.fill();
      });

      // ── Background stalls ──
      bgStalls.forEach(s => {
        if (state === "playing") { s.x -= 1.1; if (s.x < -90) s.x = W + 80 + Math.random() * 400; }
        drawBgStall(s);
      });

      // ── Ground ──
      ctx.fillStyle = "#100c22"; ctx.fillRect(0, GY, W, H - GY);
      ctx.fillStyle = "#0d0a1e"; ctx.fillRect(0, GY + 2, W, 15);
      ctx.strokeStyle = "rgba(255,255,255,0.07)"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(0, GY); ctx.lineTo(W, GY); ctx.stroke();
      // Ground dashes
      for (let gx = (tick * 1.5) % 120; gx < W; gx += 120) {
        ctx.strokeStyle = "rgba(255,255,255,0.05)"; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(gx, GY + 8); ctx.lineTo(gx + 30, GY + 8); ctx.stroke();
      }

      // ── Game logic ──
      if (state === "playing") {
        score++;
        speed = Math.min(4.5 + score / 380, 13);
        legPhase += onGround ? 0.19 : 0.06;

        // Spawn
        const interval = Math.max(52, 115 - score / 28);
        if (tick % Math.round(interval) === 0) spawnObstacle();

        // Physics
        rvy += GRAVITY;
        ry  += rvy;
        if (ry >= GY - RH) { ry = GY - RH; rvy = 0; onGround = true; jumpCount = 0; }

        // Obstacles
        obstacles = obstacles.filter(o => {
          o.x -= speed;
          drawObstacle(o);
          const hit =
            RX + 6 < o.x + o.w - 4 &&
            RX + RW - 6 > o.x + 4 &&
            ry + 10 < o.y + o.h - 4 &&
            ry + RH - 4 > o.y + 4;
          if (hit) die();
          return o.x > -60;
        });
      } else if (state === "dead") {
        obstacles.forEach(o => drawObstacle(o));
      }

      // ── Particles ──
      particles = particles.filter(p => {
        p.x += p.vx; p.y += p.vy; p.vy += 0.28; p.life--;
        const a = p.life / p.maxLife;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r * a, 0, Math.PI * 2);
        ctx.fillStyle = p.color; ctx.globalAlpha = a;
        ctx.fill(); ctx.globalAlpha = 1;
        return p.life > 0;
      });

      // ── Runner ──
      drawRunner(state === "dead");

      // ── HUD ──
      drawHUD();

      // ── Overlays ──
      if (state === "idle") drawIdleScreen();
      else if (state === "dead") drawDeadScreen();

      ctx.restore();
      raf = requestAnimationFrame(loop);
    }

    raf = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(raf);
      canvas.removeEventListener("click",      onClick);
      canvas.removeEventListener("touchstart", onTouch);
      window.removeEventListener("keydown",    onKey);
    };
  }, []);

  return (
    <PageShell
      title="Souk Runner"
      subtitle="Space / click to jump · double jump allowed · dodge invoices, price spikes & boxes"
    >
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16, maxWidth: 820, margin: "0 auto" }}>
        <canvas
          ref={canvasRef}
          width={800}
          height={320}
          style={{
            width: "100%",
            borderRadius: 12,
            border: "1px solid rgba(255,255,255,0.08)",
            cursor: "pointer",
            touchAction: "none",
            userSelect: "none",
          }}
        />

        <div style={{ display: "flex", gap: 28, fontSize: 12, color: "rgba(255,255,255,0.28)", flexWrap: "wrap", justifyContent: "center" }}>
          <span style={{ color: "#818cf8" }}>▬ Invoice</span>
          <span style={{ color: "#f87171" }}>▲ Price spike</span>
          <span style={{ color: "#fb923c" }}>■ Supply box</span>
          <span style={{ color: "rgba(255,255,255,0.4)" }}>● ● = jumps left</span>
        </div>
      </div>
    </PageShell>
  );
}
