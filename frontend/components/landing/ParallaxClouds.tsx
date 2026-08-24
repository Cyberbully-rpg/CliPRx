"use client";

import { useEffect, useRef } from "react";

export default function ParallaxClouds() {
  const bandRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const band = bandRef.current;
    const img = imgRef.current;
    if (!band || !img) return;

    const onScroll = () => {
      const r = band.getBoundingClientRect();
      const vh = window.innerHeight;
      if (r.bottom > 0 && r.top < vh) {
        const pct = (r.top + r.height) / (vh + r.height);
        img.style.transform = `translate3d(0,${(pct - 0.5) * 160}px,0)`;
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="parallax-band" ref={bandRef}>
      <img ref={imgRef} src="/assets/clouds.jpg" alt="" />
      <div className="overlay" />
      <div className="inner">
        <div style={{ maxWidth: 480 }}>
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              letterSpacing: "0.06em",
              color: "var(--text-muted)",
              textTransform: "uppercase",
            }}
          >
            above the clouds
          </span>
          <h2
            style={{
              fontFamily: "var(--font-serif-display)",
              fontSize: 40,
              lineHeight: 1.14,
              fontWeight: 400,
              color: "var(--text-heading)",
              marginTop: 10,
            }}
          >
            Your cloud spend, ranked and visible.
          </h2>
        </div>
      </div>
    </div>
  );
}
