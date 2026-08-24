"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";

export default function Nav() {
  const navRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const nav = navRef.current;
    const header = document.querySelector("header");
    if (!nav || !header) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) nav.removeAttribute("data-paper");
        else nav.setAttribute("data-paper", "");
      },
      { threshold: 0.08 }
    );
    observer.observe(header);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="nav-wrap l-nav-shell">
      <nav ref={navRef} className="nav-inner l-nav">
        <Link href="#top" className="nav-logo l-nav-logo">
          <span className="nav-dot l-nav-dot" />
          CliPRx
        </Link>
        <div className="l-nav-links">
          <Link href="/app" className="glow-btn l-nav-start">
            Start now →
          </Link>
          <Link href="#mechanism" className="navlink">
            Product
          </Link>
          <Link href="#sample" className="navlink">
            Sample report
          </Link>
          <Link href="#docs" className="navlink">
            Docs
          </Link>
        </div>
        <Link href="/login" className="nav-cta l-nav-cta">
          Log in
        </Link>
      </nav>
    </div>
  );
}
