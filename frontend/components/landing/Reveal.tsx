"use client";

import { ReactNode, useEffect, useRef } from "react";

interface RevealProps {
  as?: "div" | "section";
  className?: string;
  id?: string;
  style?: React.CSSProperties;
  children: ReactNode;
}

/** Adds the .visible class once the element scrolls into view, matching the
 * source design's IntersectionObserver-driven .reveal/.stagger classes. */
export default function Reveal({ as = "div", className = "", id, style, children }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("visible");
          observer.unobserve(el);
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const Tag = as as any;
  return (
    <Tag ref={ref} id={id} className={className} style={style}>
      {children}
    </Tag>
  );
}
