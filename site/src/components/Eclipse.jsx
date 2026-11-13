import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, Line } from "@react-three/drei";
import * as THREE from "three";
import { Bot, Cpu, Landmark } from "lucide-react";
import { prefersReducedMotion } from "../motion.js";

// The project's name as a picture: "steps in front of the bad payment, stays in the background
// otherwise". Two dotted globes with lat/long grids: the checker (lilac sun) and the Guardian (dim
// moon). A stream of payments from the agent crosses the sun. As you scroll, the Guardian slides in
// front; at totality the corona flares and bad payments (pink) hit it and scatter.
// Loaded lazily (React.lazy) so three.js never blocks the first paint or the prerender.

const SUN_R = 1.25;
const MOON_R = 1.28;
const MOON_X = 2.3;
const COUNT = 80;
const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

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

// Corona: dots in a flat ring around the sun, denser near the limb.
function coronaPoints(count) {
  const out = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const a = Math.random() * Math.PI * 2;
    const streamer = Math.pow(Math.abs(Math.sin(a * 3)), 6) * 0.8;
    const d = SUN_R * 1.06 + Math.pow(Math.random(), 2.4) * (0.7 + streamer);
    out[i * 3] = Math.cos(a) * d; out[i * 3 + 1] = Math.sin(a) * d; out[i * 3 + 2] = -0.2;
  }
  return out;
}

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

// Payments from the agent crossing the sun; bad ones (pink) bounce off the Guardian at totality.
function Particles({ occ }) {
  const ref = useRef();
  const state = useMemo(() => {
    const pos = new Float32Array(COUNT * 3);
    const col = new Float32Array(COUNT * 3);
    const good = new THREE.Color("#EDB1E8"), bad = new THREE.Color("#FF8FB0");
    const p = [];
    for (let i = 0; i < COUNT; i++) {
      const isBad = i % 4 === 0;
      p.push({ x: -5.5 + Math.random() * 11, y: (Math.random() - 0.5) * 1.6, vx: 0.5 + Math.random() * 0.5, vy: 0, bad: isBad, hit: 0 });
      (isBad ? bad : good).toArray(col, i * 3);
    }
    return { pos, col, p };
  }, []);
  useFrame((_, dtRaw) => {
    const dt = Math.min(dtRaw, 0.05);
    const o = occ.current;
    state.p.forEach((q, i) => {
      if (q.hit > 0) {
        q.x += q.vx * dt; q.y += q.vy * dt; q.hit -= dt;
        if (q.hit <= 0) { q.x = -5.6; q.y = (Math.random() - 0.5) * 1.6; q.vx = 0.5 + Math.random() * 0.5; q.vy = 0; }
      } else {
        q.x += q.vx * dt;
        if (q.bad && o > 0.7 && q.x > -MOON_R - 0.05 && q.x < 0 && Math.abs(q.y) < MOON_R) {
          q.hit = 0.9; q.vx = -0.6 - Math.random() * 0.8; q.vy = (Math.random() - 0.5) * 2.4;
        }
        if (q.x > 5.6) { q.x = -5.6; q.y = (Math.random() - 0.5) * 1.6; }
      }
      state.pos[i * 3] = q.x; state.pos[i * 3 + 1] = q.y; state.pos[i * 3 + 2] = 1.6;
    });
    ref.current.geometry.attributes.position.needsUpdate = true;
  });
  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[state.pos, 3]} />
        <bufferAttribute attach="attributes-color" args={[state.col, 3]} />
      </bufferGeometry>
      <pointsMaterial size={0.07} vertexColors transparent sizeAttenuation depthWrite={false} />
    </points>
  );
}

function Node({ position, Icon, label, filled }) {
  return (
    <Html position={position} center zIndexRange={[3, 0]}>
      <span className={`pnode${filled ? " filled" : ""}`}>
        <Icon size={filled ? 20 : 17} strokeWidth={1.6} aria-hidden="true" />
        <em>{label}</em>
      </span>
    </Html>
  );
}

function Scene({ progress, pointer, reduce }) {
  // On wide canvases the eclipse sits left of centre so the overlay text has room on the right.
  const { viewport, camera } = useThree();
  // The Agent node sits nearer the camera (z 1.6), where the visible width is smaller than at z 0;
  // clamp it against that width so its ring and label never cross the canvas edge.
  const agentHalfW = viewport.getCurrentViewport(camera, [0, 0, 1.6]).width / 2;
  const offsetX = viewport.aspect > 1.3 ? -viewport.width * 0.22 : 0;
  const group = useRef();
  const sun = useRef();
  const moon = useRef();
  const corona = useRef();
  const occ = useRef(0);
  const sunDots = useMemo(() => landPoints(SUN_R, 7000, 0), []);
  const moonDots = useMemo(() => landPoints(MOON_R, 6000, 1.7), []);
  const coronaDots = useMemo(() => coronaPoints(2600), []);

  useFrame(({ clock }) => {
    // Scroll progress through the section → how far the Guardian has moved in front.
    occ.current += (smooth(0.18, 0.5, progress.current ?? 0) - occ.current) * (reduce ? 1 : 0.08);
    const o = occ.current;
    const t = reduce ? 0 : clock.elapsedTime;
    if (sun.current) sun.current.rotation.y = 0.6 + t * 0.08;
    if (moon.current) { moon.current.position.x = (1 - o) * MOON_X; moon.current.rotation.y = -t * 0.06; }
    if (corona.current) {
      corona.current.material.opacity = 0.2 + o * 0.8;
      corona.current.scale.setScalar(0.92 + o * 0.16 + Math.sin(t * 1.4) * 0.012);
      corona.current.rotation.z = t * 0.03;
    }
    const g = group.current;
    if (g) {
      // Follows the cursor: the whole eclipse turns toward it and drifts a little after it.
      const px = reduce ? 0 : pointer.current.x, py = reduce ? 0 : pointer.current.y;
      g.rotation.y += (px * 0.7 - g.rotation.y) * 0.06;
      g.rotation.x += (0.1 + py * 0.45 - g.rotation.x) * 0.06;
      g.position.x += (offsetX + px * 0.35 - g.position.x) * 0.06;
      g.position.y += (-py * 0.25 - g.position.y) * 0.06;
    }
  });

  return (
    <group ref={group} position={[offsetX, 0, 0]}>
      <points ref={corona}>
        <bufferGeometry><bufferAttribute attach="attributes-position" args={[coronaDots, 3]} /></bufferGeometry>
        <pointsMaterial color="#F2C2EE" size={0.026} sizeAttenuation transparent opacity={0.2} depthWrite={false} blending={THREE.AdditiveBlending} />
      </points>
      {/* The sun: the checker */}
      <group ref={sun}>
        <DottedGlobe r={SUN_R} dots={sunDots} dotColor="#E39BDE" dotSize={0.032} gridColor="#C77DC6" gridOpacity={0.35} core="#1b1022" />
      </group>
      {/* The moon: the Guardian, sliding in front */}
      <group ref={moon} position={[MOON_X, 0, 0.9]}>
        <DottedGlobe r={MOON_R} dots={moonDots} dotColor="#6E6588" dotSize={0.026} gridColor="#3A3550" gridOpacity={0.6} core="#0b0910" />
        <Node position={[0, -MOON_R - 0.25, 0]} Icon={Landmark} label="Guardian" filled />
      </group>
      <Particles occ={occ} />
      <Node position={[Math.max(-2.0, -agentHalfW + 1.3 - offsetX), 1.15, 1.6]} Icon={Bot} label="Agent" />
      <Node position={[0, SUN_R + 0.45, 0]} Icon={Cpu} label="Checker" />
    </group>
  );
}

export default function Eclipse({ progress }) {
  const wrap = useRef(null);
  const pointer = useRef({ x: 0, y: 0 });
  const [onScreen, setOnScreen] = useState(true);
  const reduce = prefersReducedMotion();

  useEffect(() => {
    const el = wrap.current;
    const io = new IntersectionObserver(([e]) => setOnScreen(e.isIntersecting));
    io.observe(el);
    // Listen on the whole stage, so the cursor over the step cards still turns the eclipse.
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
        <Scene progress={progress} pointer={pointer} reduce={reduce} />
      </Canvas>
    </div>
  );
}
