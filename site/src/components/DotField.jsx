import { useEffect, useRef } from "react";
import { prefersReducedMotion } from "../motion.js";

// Lilac-card texture: white dots on a 7px grid, a slow shimmer band, a cream glow from the bottom
// centre (glow.current.v, tweened by GSAP) and brighter dots around the cursor.
// Fast path: the dot grid is drawn once into an offscreen canvas; each frame only composites
// images and gradients (a handful of draw calls), at most 30 times a second.
// Decorative: hidden from assistive tech. Pauses off screen; one static frame under reduced motion.
export function DotField({ glow }) {
  const ref = useRef(null);

  useEffect(() => {
    const canvas = ref.current;
    const host = canvas.parentElement;
    const ctx = canvas.getContext("2d");
    const reduce = prefersReducedMotion();
    const dots = document.createElement("canvas");
    const band = document.createElement("canvas");
    const dctx = dots.getContext("2d");
    const bctx = band.getContext("2d");
    const pointer = { x: -1e4, y: -1e4 };
    let w = 0, h = 0, dpr = 1, raf = 0, visible = true, last = 0;

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = host.clientWidth; h = host.clientHeight;
      for (const c of [canvas, dots, band]) { c.width = Math.round(w * dpr); c.height = Math.round(h * dpr); }
      canvas.style.width = `${w}px`; canvas.style.height = `${h}px`;
      for (const c of [ctx, dctx, bctx]) c.setTransform(dpr, 0, 0, dpr, 0, 0);
      // Dot grid, drawn once per size.
      dctx.clearRect(0, 0, w, h);
      dctx.fillStyle = "#fff";
      for (let y = 3.5; y < h; y += 7) for (let x = 3.5; x < w; x += 7) dctx.fillRect(x - 0.8, y - 0.8, 1.6, 1.6);
    };

    const draw = (t) => {
      const g = glow?.current?.v ?? 1;
      const s = t / 1000;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      // Cream glow from the bottom centre.
      const rad = ctx.createRadialGradient(w / 2, h * 1.05, 0, w / 2, h * 1.05, Math.max(w, h) * 0.75);
      rad.addColorStop(0, `rgba(255, 243, 251, ${0.75 * g})`);
      rad.addColorStop(1, "rgba(255, 243, 251, 0)");
      ctx.fillStyle = rad;
      ctx.fillRect(0, 0, w, h);
      // Base dots.
      ctx.globalAlpha = 0.14;
      ctx.drawImage(dots, 0, 0, w, h);
      ctx.globalAlpha = 1;
      // Bright dots: the same grid masked by a drifting diagonal band and the cursor lens.
      bctx.globalCompositeOperation = "source-over";
      bctx.setTransform(1, 0, 0, 1, 0, 0);
      bctx.clearRect(0, 0, band.width, band.height);
      bctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      bctx.drawImage(dots, 0, 0, w, h);
      bctx.globalCompositeOperation = "destination-in";
      const span = w + h;
      const off = ((s * 60) % span) - h;
      const lin = bctx.createLinearGradient(off, 0, off + h, h);
      lin.addColorStop(0, "rgba(255,255,255,0)");
      lin.addColorStop(0.5, "rgba(255,255,255,0.18)");
      lin.addColorStop(1, "rgba(255,255,255,0)");
      bctx.fillStyle = lin;
      bctx.fillRect(0, 0, w, h);
      ctx.drawImage(band, 0, 0, w, h);
      if (pointer.x > -1e3) {
        bctx.globalCompositeOperation = "source-over";
        bctx.setTransform(1, 0, 0, 1, 0, 0);
        bctx.clearRect(0, 0, band.width, band.height);
        bctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        bctx.drawImage(dots, 0, 0, w, h);
        bctx.globalCompositeOperation = "destination-in";
        const lens = bctx.createRadialGradient(pointer.x, pointer.y, 0, pointer.x, pointer.y, 140);
        lens.addColorStop(0, "rgba(255,255,255,0.7)");
        lens.addColorStop(1, "rgba(255,255,255,0)");
        bctx.fillStyle = lens;
        bctx.fillRect(pointer.x - 140, pointer.y - 140, 280, 280);
        ctx.drawImage(band, 0, 0, w, h);
      }
    };

    const loop = (t) => {
      raf = requestAnimationFrame(loop);
      if (!visible || t - last < 33) return; // ~30 fps is plenty for a slow texture
      last = t;
      draw(t);
    };
    const onMove = (e) => {
      const r = canvas.getBoundingClientRect();
      pointer.x = ((e.clientX - r.left) / r.width) * w;
      pointer.y = ((e.clientY - r.top) / r.height) * h;
    };
    const onLeave = () => { pointer.x = pointer.y = -1e4; };

    resize();
    const ro = new ResizeObserver(() => { resize(); draw(performance.now()); });
    ro.observe(host);
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; });
    io.observe(canvas);

    if (reduce) draw(0);
    else {
      host.addEventListener("pointermove", onMove);
      host.addEventListener("pointerleave", onLeave);
      raf = requestAnimationFrame(loop);
    }
    return () => {
      cancelAnimationFrame(raf); ro.disconnect(); io.disconnect();
      host.removeEventListener("pointermove", onMove);
      host.removeEventListener("pointerleave", onLeave);
    };
  }, [glow]);

  return <canvas ref={ref} className="dotfield" aria-hidden="true" />;
}
