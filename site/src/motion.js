// Motion helpers shared by the page and its canvases. Browser-only code runs inside effects,
// so the prerender (scripts/prerender.mjs) can import this file in Node.
export function prefersReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

// Lenis smooth scroll driven by GSAP's ticker, plus every scroll and load tween on the page.
// `refs` carries the mutable values canvases read each frame (glows, scroll progress).
export async function startMotion(refs) {
  if (prefersReducedMotion()) return () => {};
  const [{ gsap }, { ScrollTrigger }, { default: Lenis }] = await Promise.all([
    import("gsap"), import("gsap/ScrollTrigger"), import("lenis"),
  ]);
  gsap.registerPlugin(ScrollTrigger);

  const lenis = new Lenis();
  lenis.on("scroll", ScrollTrigger.update);
  const tick = (t) => lenis.raf(t * 1000);
  gsap.ticker.add(tick);
  gsap.ticker.lagSmoothing(0);

  const ctx = gsap.context(() => {
    const q = (s) => gsap.utils.toArray(s);

    // Hero: load-in, then scroll away.
    gsap.from(".hero", { scale: 0.96, borderRadius: 32, duration: 1.2, ease: "power3.out", clearProps: "transform" });
    gsap.from(".hero-in > *", { y: 30, duration: 1, stagger: 0.08, ease: "power3.out", delay: 0.1 });
    gsap.from(".hero .console", { y: 60, duration: 1.2, ease: "power3.out", delay: 0.2, clearProps: "transform" });
    const heroScroll = { trigger: ".hero", start: "top top", end: "bottom top", scrub: true };
    gsap.to(".hero-in", { yPercent: -18, ease: "none", scrollTrigger: heroScroll });
    gsap.to(".hero .console-wrap", { yPercent: -30, ease: "none", scrollTrigger: heroScroll });
    gsap.fromTo(refs.heroGlow.current, { v: 1 }, { v: 0.25, ease: "none", scrollTrigger: heroScroll });

    // Fixed mini header once the hero has scrolled past.
    ScrollTrigger.create({
      trigger: ".hero", start: "bottom 80px",
      onEnter: () => document.body.classList.add("mini-on"),
      onLeaveBack: () => document.body.classList.remove("mini-on"),
    });

    // Reveals in both scroll directions. Scrolling down, a block rises in from below as it enters;
    // scrolling back up, it drops in from above as it re-enters at the top. Leaving the screen fades
    // it out, so the motion replays each time. Blocks in view at load start visible.
    const reveal = (targets, trigger, { dist = 36, stagger = 0 } = {}) => {
      const show = (from) => gsap.fromTo(targets, { y: from, opacity: 0 }, {
        y: 0, opacity: 1, duration: 0.8, stagger, ease: "power3.out", overwrite: true,
      });
      const hide = () => gsap.to(targets, { opacity: 0, duration: 0.25, overwrite: true });
      const st = ScrollTrigger.create({
        trigger, start: "top 88%", end: "bottom 12%",
        onEnter: () => show(dist),
        onEnterBack: () => show(-dist),
        onLeave: hide,
        onLeaveBack: hide,
      });
      if (!st.isActive) gsap.set(targets, { opacity: 0 });
    };
    // Section heads: title and lead paragraph, in order.
    // A sticky heading (FAQ, Try it) uses its whole side-by-side block as the trigger, so it isn't
    // faded out while it is still pinned on screen.
    q(".head2").forEach((head) => reveal(head.querySelectorAll("h2, p"), head.closest(".faq-split, .side-split") || head, { stagger: 0.08 }));
    // FAQ cards, one after another.
    reveal(q(".faq-item"), ".faq", { dist: 24, stagger: 0.04 });
    // Groups of cards, callouts and steps: each row moves as one block so its cards stay level.
    const groups = [".callouts", ".psteps", ".steps", ".grid4", ".cards", ".tiers", ".bento", ".rstats", ".dbento", ".vgrid", ".rules", ".caps",
      ".vx", ".ad", ".split", ".tablewrap", ".rgrid", ".receipts-panel", ".term-win", ".caveats"];
    groups.forEach((sel) => q(sel).forEach((group) => reveal(group, group)));

    // Same attack: Morse field progress, ASCII boxes drift in, lilac panel wipes up.
    ScrollTrigger.create({
      trigger: "#problem .split", start: "top bottom", end: "bottom top",
      onUpdate: (st) => { refs.morseProgress.current = st.progress; },
    });
    // Incident cards drift in on wide screens only; at phone width the rotation pushes them off screen.
    const wideScreen = window.matchMedia("(min-width: 761px)").matches;
    if (wideScreen) q(".ascii").forEach((box, i) => {
      const s = i % 2 ? 1 : -1;
      gsap.fromTo(box, { x: 60 * s, y: 40, rotation: 6 * s }, {
        x: 0, y: 0, rotation: 0, ease: "none",
        scrollTrigger: { trigger: box, start: "top bottom", end: "center center", scrub: true },
      });
      gsap.to(box.firstElementChild, { y: 8, duration: 2.4 + i * 0.3, repeat: -1, yoyo: true, ease: "sine.inOut" });
    });
    gsap.fromTo(".calm", { clipPath: "inset(100% 0 0 0)" }, {
      clipPath: "inset(0% 0 0 0)", ease: "none",
      scrollTrigger: { trigger: ".calm", start: "top 75%", end: "center 55%", scrub: true },
    });
    gsap.from(".okchip", {
      scale: 0.6, duration: 0.7, ease: "back.out(2)",
      scrollTrigger: { trigger: ".calm", start: "center 60%" },
    });

    // Diagram arrows draw in; result bars grow.
    // Diagram, scroll-driven: steps light up in payment order as the diagram scrolls through the
    // viewport (scrubbed, so scrolling back reverses it). Arrows draw as their step arrives.
    const adSvg = document.querySelector(".ad-svg");
    if (adSvg) {
      const tl = gsap.timeline({
        scrollTrigger: { trigger: adSvg, start: "top 85%", end: "bottom 95%", scrub: 0.6 },
        defaults: { ease: "none" },
      });
      for (let k = 0; k <= 8; k++) {
        const items = adSvg.querySelectorAll(`[data-at="${k}"]`);
        const paths = adSvg.querySelectorAll(`.ad-arrow[data-at="${k}"] path`);
        const boxes = [...items].filter((el) => !el.classList.contains("ad-arrow"));
        if (paths.length) {
          // Fade the whole arrow (line, head and label) in as its line draws, so no head shows early.
          tl.fromTo(adSvg.querySelectorAll(`.ad-arrow[data-at="${k}"]`), { opacity: 0.3 }, { opacity: 1, duration: 0.3 }, k);
          tl.fromTo(paths, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.6 }, k);
        }
        // Opacity only: a transform on SVG groups can misplace them, and a low floor read as missing boxes.
        if (boxes.length) tl.fromTo(boxes, { opacity: 0.4 }, { opacity: 1, duration: 0.6 }, k + 0.3);
        const flows = adSvg.querySelectorAll(`[data-flow-at="${k}"]`);
        if (flows.length) tl.fromTo(flows, { opacity: 0 }, { opacity: 1, duration: 0.3 }, k + 0.4);
      }
    }
    // Payment-path list (phones), scroll-driven: steps slide in one by one, the connector lines draw
    // down between them, and the step at mid-screen is highlighted.
    const adItems = q(".ad-list li");
    if (adItems.length && window.matchMedia("(max-width: 760px)").matches) {
      adItems.forEach((li, k) => {
        gsap.fromTo(li, { x: -40, opacity: 0 }, {
          x: 0, opacity: 1, ease: "power2.out",
          scrollTrigger: { trigger: li, start: "top 92%", end: "top 62%", scrub: 0.5 },
        });
        if (k > 0) gsap.fromTo(li, { "--grow": 0 }, {
          "--grow": 1, ease: "none",
          scrollTrigger: { trigger: li, start: "top 95%", end: "top 70%", scrub: 0.5 },
        });
        ScrollTrigger.create({ trigger: li, start: "top 55%", end: "bottom 55%", toggleClass: { targets: li, className: "ad-live" } });
      });
    }

    // Results, scroll-driven (scrubbed, so scrolling back reverses each effect).
    // Counters land on the exact committed numbers; the markup keeps the real values for crawlers.
    // The text is computed from the trigger's own progress on every update and refresh, so it can
    // never get stuck at 0 after the page re-measures.
    const counter = (el, startAt, endAt, trigger) => {
      // Remember the real value once; a re-run (hot reload, remount) must not read a mid-count number.
      if (!el.dataset.final) el.dataset.final = el.textContent.trim();
      const m = el.dataset.final.match(/^(\d+(?:\.\d+)?)(.*)$/);
      if (!m) return;
      const target = +m[1], decimals = (m[1].split(".")[1] || "").length, rest = m[2];
      const paint = (p) => { el.textContent = (target * p).toFixed(decimals) + rest; };
      ScrollTrigger.create({
        trigger, start: startAt, end: endAt,
        onUpdate: (st) => paint(st.progress),
        onRefresh: (st) => paint(st.progress),
      });
    };
    // 1. Headline numbers count up.
    q(".rstat strong").forEach((el) => counter(el, "top 92%", "top 55%", el.closest(".rstats")));
    // 2. Table rows sweep in from the left, one after another, as the table scrolls through.
    const resRows = q(".results-table tbody tr");
    if (resRows.length) {
      gsap.fromTo(resRows, { x: -48, opacity: 0 }, {
        x: 0, opacity: 1, stagger: 0.12, ease: "power2.out",
        scrollTrigger: { trigger: ".results-table tbody", start: "top 88%", end: "bottom 75%", scrub: 0.5 },
      });
      // The row at the middle of the screen gets the lilac reading line.
      resRows.forEach((row) => ScrollTrigger.create({
        trigger: row, start: "top 55%", end: "bottom 55%", toggleClass: { targets: row, className: "row-live" },
      }));
    }
    // 3. Chart bars grow with the scroll, pair by pair; their value labels follow.
    const chart = document.querySelector(".results-chart svg");
    if (chart) {
      const rects = chart.querySelectorAll("rect");
      const labels = [...rects].map((r) => r.parentNode.querySelector("text"));
      const tl = gsap.timeline({ scrollTrigger: { trigger: chart, start: "top 85%", end: "bottom 65%", scrub: 0.5 } });
      rects.forEach((r, k) => {
        // Animate the bar's width attribute (no transforms, so nothing can drift off its axis).
        if (!r.dataset.w) r.dataset.w = r.getAttribute("width");
        gsap.set(r, { clearProps: "transform" });
        tl.fromTo(r, { attr: { width: 0 } }, { attr: { width: +r.dataset.w }, ease: "power2.out", duration: 1 }, k * 0.25);
        if (labels[k]) tl.fromTo(labels[k], { opacity: 0, x: -12 }, { opacity: 1, x: 0, duration: 0.6 }, k * 0.25 + 0.5);
      });
    }
    // 4. Family bars fill and their counts climb.
    const fam = document.querySelector(".families ul");
    if (fam) {
      gsap.fromTo(fam.querySelectorAll(".fam-bar > span"), { scaleX: 0 }, {
        scaleX: 1, transformOrigin: "left center", stagger: 0.12, ease: "power2.out",
        scrollTrigger: { trigger: fam, start: "top 88%", end: "bottom 60%", scrub: 0.5 },
      });
      fam.querySelectorAll(".fam-val").forEach((el) => counter(el, "top 88%", "bottom 60%", fam));
    }

    // Closing card: glow rises, tiles float up through the card and follow the cursor.
    const closing = document.querySelector(".cta");
    if (closing) {
      gsap.fromTo(refs.ctaGlow.current, { v: 0.4 }, {
        v: 1, ease: "none", scrollTrigger: { trigger: closing, start: "top bottom", end: "center center", scrub: true },
      });
      // Tiles assemble when the primary button is hovered or focused (CSS, see .cta.assembled).
      // Clusters lean a little toward the pointer.
      const clusters = q(".cta-cluster").map((el, k) => ({
        x: gsap.quickTo(el, "x", { duration: 0.9, ease: "power3.out" }),
        y: gsap.quickTo(el, "y", { duration: 0.9, ease: "power3.out" }),
        d: k ? 18 : 12,
      }));
      closing.addEventListener("pointermove", (e) => {
        const r = closing.getBoundingClientRect();
        const dx = (e.clientX - r.left) / r.width - 0.5;
        const dy = (e.clientY - r.top) / r.height - 0.5;
        clusters.forEach((c) => { c.x(dx * c.d); c.y(dy * c.d); });
      });
      closing.addEventListener("pointerleave", () => clusters.forEach((c) => { c.x(0); c.y(0); }));
    }
  });

  document.fonts?.ready.then(() => ScrollTrigger.refresh());
  // Content that loads later (the live receipts, the globe) changes the page height; re-measure every
  // trigger when it does, or the ones further down fire at the wrong scroll position.
  let lastH = document.body.scrollHeight, refreshTimer = 0;
  const heightWatch = new ResizeObserver(() => {
    const h = document.body.scrollHeight;
    if (Math.abs(h - lastH) < 2) return;
    lastH = h;
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(() => ScrollTrigger.refresh(), 150);
  });
  heightWatch.observe(document.body);

  return () => {
    heightWatch.disconnect();
    clearTimeout(refreshTimer);
    ctx.revert();
    // Put the real numbers back so a later run starts from them.
    document.querySelectorAll("[data-final]").forEach((el) => { el.textContent = el.dataset.final; });
    document.querySelectorAll(".results-chart rect[data-w]").forEach((r) => r.setAttribute("width", r.dataset.w));
    gsap.ticker.remove(tick);
    lenis.destroy();
    document.body.classList.remove("mini-on");
  };
}
