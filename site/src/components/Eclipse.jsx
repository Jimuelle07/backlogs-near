import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, Line } from "@react-three/drei";
import * as THREE from "three";
import { Ban, Bot, Check, Cpu, Hourglass, Landmark, Store } from "lucide-react";
import { prefersReducedMotion } from "../motion.js";
import { ROWS } from "./Console.jsx";

// The three steps beside it, acted out on the hero console's sample payments, one at a time:
// 1 the agent asks: the payment travels from the agent to the Guardian (the globe: it holds the funds);
// 2 the checker decides: the Guardian pauses it and a signal goes up to the checker and back;
// 3 only the contract pays: allow goes on to the payee; hold circles the Guardian in escrow;
//   block: the corona flares (the Guardian "steps in front") and the payment bounces back unpaid.
// onStep(i) reports the phase so the matching step card lights up.
// Loaded lazily (React.lazy) so three.js never blocks the first paint or the prerender.

const R = 1.0; // Guardian globe
const AGENT_X = -2.55;
const PAYEE_X = 2.55;
const CHECK_Y = 1.9;
const Z = 1.2; // how far the payment rises in front of the globe while it crosses it
const HOLD_R = 1.42;
const ASK = 1.3, DECIDE = 1.4, OUT = 1.9, REST = 0.5;
const CYCLE = ASK + DECIDE + OUT + REST;
// dns-renew (allow), hostc0 (block), hostco (allow), supplier (hold).
const ORDER = [3, 0, 1, 2].map((i) => ROWS[i]);
const VERDICT = { allow: "ALLOW · paid", hold: "HOLD · in escrow", block: "BLOCK · not paid" };
const COLOR = { ask: new THREE.Color("#EEEAF5"), allow: new THREE.Color("#EDB1E8"), hold: new THREE.Color("#EEEAF5"), block: new THREE.Color("#FF8FB0") };
const LILAC = new THREE.Color("#F2C2EE");

const clamp01 = (x) => Math.min(1, Math.max(0, x));
const ease = (x) => { const t = clamp01(x); return t * t * (3 - 2 * t); };
const easeOut = (x) => 1 - Math.pow(1 - clamp01(x), 3);
// The payment path runs at z = 0, through the Guardian; the dot lifts in front of the globe to cross it.
const lift = (x) => Z * (1 - ease((Math.abs(x) - R * 0.6) / (R * 0.65)));

// Fibonacci points kept where an abstract sine "land" mask is high (not a real map).
function landPoints(r, count, seed = 0) {
  const out = [];
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2;
    const rr = Math.sqrt(1 - y * y);
    const th = golden * i;
    const x = Math.cos(th) * rr, z = Math.sin(th) * rr;
    const lat = Math.asin(y), lon = Math.atan2(z, x) + seed;
    const land = Math.sin(lon * 3 + Math.sin(lat * 2.4) * 1.6) * Math.cos(lat * 2.2) + Math.sin(lon * 5 - lat * 3) * 0.35;
    if (land > -0.05) out.push(x * r, y * r, z * r);
  }
  return new Float32Array(out);
}

// Latitude and longitude circles.
function gridLines(r) {
  const lines = [];
  const ring = (fn) => { const pts = []; for (let a = 0; a <= 360; a += 8) pts.push(fn(THREE.MathUtils.degToRad(a))); return pts; };
  for (let lat = -60; lat <= 60; lat += 30) {
    const la = THREE.MathUtils.degToRad(lat);
    lines.push(ring((lo) => new THREE.Vector3(Math.cos(la) * Math.cos(lo) * r, Math.sin(la) * r, Math.cos(la) * Math.sin(lo) * r)));
  }
  for (let lon = 0; lon < 180; lon += 30) {
    const lo = THREE.MathUtils.degToRad(lon);
    lines.push(ring((la) => new THREE.Vector3(Math.cos(la) * Math.cos(lo) * r, Math.sin(la) * r, Math.cos(la) * Math.sin(lo) * r)));
  }
  return lines;
}

// Corona: dots in a flat ring around the globe, denser near the limb.
function coronaPoints(count) {
  const out = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const a = Math.random() * Math.PI * 2;
    const streamer = Math.pow(Math.abs(Math.sin(a * 3)), 6) * 0.6;
    const d = R * 1.06 + Math.pow(Math.random(), 2.4) * (0.55 + streamer);
    out[i * 3] = Math.cos(a) * d; out[i * 3 + 1] = Math.sin(a) * d; out[i * 3 + 2] = -0.2;
  }
  return out;
}

const circle = (r, z = 0) => Array.from({ length: 73 }, (_, i) => new THREE.Vector3(Math.cos(i * Math.PI / 36) * r, Math.sin(i * Math.PI / 36) * r, z));

// A globe in the site's style: dark core, lat/long grid, dotted land.
function DottedGlobe({ r, dots, dotColor, dotSize, gridColor, gridOpacity, core }) {
  const grid = useMemo(() => gridLines(r * 1.003), [r]);
  return (
    <>
      <mesh><sphereGeometry args={[r * 0.985, 48, 48]} /><meshBasicMaterial color={core} /></mesh>
      {grid.map((pts, k) => <Line key={k} points={pts} color={gridColor} lineWidth={1} transparent opacity={gridOpacity} />)}
      <points>
        <bufferGeometry><bufferAttribute attach="attributes-position" args={[dots, 3]} /></bufferGeometry>
        <pointsMaterial color={dotColor} size={dotSize} sizeAttenuation transparent depthWrite={false} />
      </points>
    </>
  );
}

function Node({ position, Icon, label, filled, nodeRef }) {
  return (
    <Html position={position} center zIndexRange={[3, 0]}>
      <span ref={nodeRef} className={`pnode${filled ? " filled" : ""}`}>
        <Icon size={filled ? 20 : 17} strokeWidth={1.6} aria-hidden="true" />
        <em>{label}</em>
      </span>
    </Html>
  );
}

// One payment at a time: position, colour and labels follow the timeline above.
function Payment({ corona, checker, payee, onStep }) {
  const time = useRef(0);
  const last = useRef({ k: -1, step: -1, verdict: null, paid: false });
  const dot = useRef();
  const pulse = useRef();
  const ring = useRef();
  const label = useRef();
  const amount = useRef();
  const payeeName = useRef();
  const verdict = useRef();
  const why = useRef();
  const ringPts = useMemo(() => circle(HOLD_R), []);

  useFrame((_, dt) => {
    time.current += Math.min(dt, 0.05);
    const k = Math.floor(time.current / CYCLE);
    const t = time.current - k * CYCLE;
    const [kind, to, amt, reason] = ORDER[k % ORDER.length];
    const l = last.current;
    if (l.k !== k) {
      l.k = k;
      amount.current.textContent = `${amt.toFixed(2)} tUSDC`;
      payeeName.current.textContent = to;
      why.current.textContent = reason;
    }

    const step = t < ASK ? 0 : t < ASK + DECIDE ? 1 : 2;
    if (step !== l.step) { l.step = step; onStep?.(step); checker.current?.classList.toggle("on", step === 1); }
    const shown = t >= ASK + DECIDE * 0.8 ? kind : "";
    if (shown !== l.verdict) { l.verdict = shown; verdict.current.dataset.v = shown; }
    const paid = kind === "allow" && t > ASK + DECIDE + OUT * 0.6;
    if (paid !== l.paid) { l.paid = paid; payee.current?.classList.toggle("on", paid); }

    let x = 0, y = 0, z = null, alpha = 1, color = COLOR.ask, flare = 0, ringOn = 0;
    const p = dot.current.position;
    if (step === 0) {
      x = THREE.MathUtils.lerp(AGENT_X + 0.4, 0, ease(t / ASK));
      alpha = clamp01(t / 0.25);
    } else if (step === 1) {
      const v = (t - ASK) / DECIDE;
      dot.current.scale.setScalar(1 + Math.sin(v * Math.PI * 4) * 0.18);
      const up = v < 0.5 ? ease(v * 2) : 1 - ease((v - 0.5) * 2);
      pulse.current.position.set(0, THREE.MathUtils.lerp(R + 0.05, CHECK_Y - 0.32, up), 0.3);
      pulse.current.material.opacity = Math.sin(clamp01(v) * Math.PI);
      color = v > 0.8 ? COLOR[kind] : COLOR.ask;
    } else {
      const u = (t - ASK - DECIDE) / OUT;
      color = COLOR[kind];
      if (kind === "allow") {
        x = THREE.MathUtils.lerp(0, PAYEE_X - 0.4, ease(u / 0.7));
        alpha = 1 - clamp01((u - 0.75) / 0.25);
      } else if (kind === "block") {
        flare = Math.sin(clamp01(u / 0.8) * Math.PI);
        x = THREE.MathUtils.lerp(0, -1.7, easeOut(u));
        y = Math.sin(easeOut(u) * Math.PI) * 0.45;
        alpha = 1 - clamp01((u - 0.4) / 0.6);
      } else {
        // Hold: out to the escrow ring, then circle the Guardian.
        ringOn = clamp01(u / 0.2);
        const a = -Math.PI / 2 - easeOut(u) * Math.PI * 1.6;
        const m = ease(u / 0.25);
        x = THREE.MathUtils.lerp(0, Math.cos(a) * HOLD_R, m);
        y = THREE.MathUtils.lerp(0, Math.sin(a) * HOLD_R, m);
        z = THREE.MathUtils.lerp(Z, 0, m);
        alpha = 1 - clamp01((u - 0.85) / 0.15);
      }
      if (t > ASK + DECIDE + OUT) alpha = 0;
    }
    if (step !== 1) { dot.current.scale.setScalar(1); pulse.current.material.opacity = 0; }
    p.set(x, y, z ?? lift(x));
    dot.current.material.color.copy(color);
    dot.current.material.opacity = alpha;
    label.current.style.opacity = alpha;
    ring.current.material.opacity = ringOn * 0.7 * (kind === "hold" && step === 2 ? 1 : 0);

    const c = corona.current;
    if (c) {
      c.material.opacity = 0.22 + flare * 0.78;
      c.material.color.copy(LILAC).lerp(COLOR.block, flare);
      c.scale.setScalar(1 + flare * 0.18);
    }
  });

  return (
    <>
      <mesh ref={dot} position={[AGENT_X + 0.4, 0, 0]}>
        <sphereGeometry args={[0.075, 20, 20]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
        <Html position={[0, 0.3, 0]} center zIndexRange={[4, 0]}>
          <span ref={label} className="gpay" style={{ opacity: 0 }}><b ref={amount} /> → <i ref={payeeName} /></span>
        </Html>
      </mesh>
      <mesh ref={pulse}>
        <sphereGeometry args={[0.05, 12, 12]} />
        <meshBasicMaterial color="#EDB1E8" transparent opacity={0} depthWrite={false} />
      </mesh>
      <Line ref={ring} points={ringPts} color="#EEEAF5" lineWidth={1} dashed dashSize={0.06} gapSize={0.06} transparent opacity={0} />
      <Html position={[0, CHECK_Y, 0.3]} zIndexRange={[4, 0]}>
        <div ref={verdict} className="gverdict" data-v="">
          <span className="vchip allow"><Check size={12} aria-hidden="true" />{VERDICT.allow}</span>
          <span className="vchip hold"><Hourglass size={12} aria-hidden="true" />{VERDICT.hold}</span>
          <span className="vchip block"><Ban size={12} aria-hidden="true" />{VERDICT.block}</span>
          <em ref={why} />
        </div>
      </Html>
    </>
  );
}

function Scene({ pointer, reduce, onStep }) {
  // On wide canvases the scene sits in the left half, beside the step cards; it scales to fit.
  const { viewport } = useThree();
  const wide = viewport.aspect > 1.3;
  const scale = Math.min(1, (wide ? viewport.width * 0.5 : viewport.width * 0.94) / 6.4, viewport.height / 4.9);
  const offsetX = wide ? -viewport.width * 0.215 : 0;
  const group = useRef();
  const globe = useRef();
  const corona = useRef();
  const checker = useRef();
  const payee = useRef();
  const dots = useMemo(() => landPoints(R, 5200, 0), []);
  const coronaDots = useMemo(() => coronaPoints(2200), []);
  const path = useMemo(() => [new THREE.Vector3(AGENT_X + 0.4, 0, 0), new THREE.Vector3(PAYEE_X - 0.4, 0, 0)], []);
  const link = useMemo(() => [new THREE.Vector3(0, R + 0.05, 0.3), new THREE.Vector3(0, CHECK_Y - 0.32, 0.3)], []);

  useFrame(({ clock }) => {
    const t = reduce ? 0 : clock.elapsedTime;
    if (globe.current) globe.current.rotation.y = 0.6 + t * 0.08;
    if (corona.current) corona.current.rotation.z = t * 0.03;
    const g = group.current;
    if (g) {
      // Turns toward the cursor (mouse anywhere over the stage, see the listener below).
      const px = reduce ? 0 : pointer.current.x, py = reduce ? 0 : pointer.current.y;
      g.rotation.y += (px * 0.15 - g.rotation.y) * 0.05;
      g.rotation.x += (py * 0.1 - g.rotation.x) * 0.05;
    }
  });

  return (
    <group ref={group} position={[offsetX, -0.15 * scale, 0]} scale={scale}>
      <points ref={corona}>
        <bufferGeometry><bufferAttribute attach="attributes-position" args={[coronaDots, 3]} /></bufferGeometry>
        <pointsMaterial color="#F2C2EE" size={0.024} sizeAttenuation transparent opacity={0.22} depthWrite={false} blending={THREE.AdditiveBlending} />
      </points>
      <group ref={globe}>
        <DottedGlobe r={R} dots={dots} dotColor="#C892CF" dotSize={0.028} gridColor="#4A3F63" gridOpacity={0.6} core="#120e18" />
      </group>
      <Line points={path} color="#5A5070" lineWidth={1} dashed dashSize={0.08} gapSize={0.07} />
      <Line points={link} color="#5A5070" lineWidth={1} dashed dashSize={0.06} gapSize={0.06} />
      <Node position={[AGENT_X, 0, 0]} Icon={Bot} label="Agent" />
      <Node position={[0, CHECK_Y, 0.3]} Icon={Cpu} label="Checker" nodeRef={checker} />
      <Node position={[0, -R - 0.32, 0.3]} Icon={Landmark} label="Guardian · holds the funds" filled />
      <Node position={[PAYEE_X, 0, 0]} Icon={Store} label="Payee" nodeRef={payee} />
      {!reduce && <Payment corona={corona} checker={checker} payee={payee} onStep={onStep} />}
    </group>
  );
}

export default function Eclipse({ onStep }) {
  const wrap = useRef(null);
  const pointer = useRef({ x: 0, y: 0 });
  const [onScreen, setOnScreen] = useState(true);
  const reduce = prefersReducedMotion();

  useEffect(() => {
    const el = wrap.current;
    const io = new IntersectionObserver(([e]) => setOnScreen(e.isIntersecting));
    io.observe(el);
    // Listen on the whole stage, so the cursor over the step cards still turns the scene.
    // Mouse only: on touch, a drag is a scroll.
    const stage = el.parentElement || el;
    const move = (e) => {
      if (e.pointerType !== "mouse") return;
      const r = el.getBoundingClientRect();
      pointer.current = { x: (e.clientX - r.left) / r.width - 0.5, y: (e.clientY - r.top) / r.height - 0.5 };
    };
    const leave = () => { pointer.current = { x: 0, y: 0 }; };
    stage.addEventListener("pointermove", move);
    stage.addEventListener("pointerleave", leave);
    return () => { io.disconnect(); stage.removeEventListener("pointermove", move); stage.removeEventListener("pointerleave", leave); };
  }, []);

  return (
    <div ref={wrap} className="globe" aria-hidden="true">
      <Canvas camera={{ position: [0, 0, 6.6], fov: 42 }} dpr={[1, 2]}
        frameloop={reduce ? "demand" : onScreen ? "always" : "never"} gl={{ antialias: true, alpha: true }}>
        <Scene pointer={pointer} reduce={reduce} onStep={onStep} />
      </Canvas>
    </div>
  );
}
