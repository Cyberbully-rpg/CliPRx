"use client";

import { AnchorHTMLAttributes, ButtonHTMLAttributes, CSSProperties, ReactNode, useState } from "react";

type Variant = "dark" | "cream" | "glass";

const base: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  height: 36,
  padding: "0 18px",
  borderRadius: "var(--radius-lg)" as unknown as string,
  fontFamily: "var(--font-sans)",
  fontSize: 14,
  fontWeight: 600,
  letterSpacing: "0.01em",
  border: "1px solid transparent",
  cursor: "pointer",
  transition: "background-color .14s ease, border-color .14s ease, box-shadow .14s ease, transform .08s ease",
  whiteSpace: "nowrap",
};

const variants: Record<Variant, { idle: CSSProperties; hover: CSSProperties }> = {
  dark: {
    idle: {
      background: "#404040",
      color: "#fff",
      borderColor: "#565654",
      boxShadow: "var(--shadow-button-dark)" as unknown as string,
    },
    hover: { background: "#4a4a49" },
  },
  cream: {
    idle: {
      background: "var(--btn-cream-bg)" as unknown as string,
      color: "var(--ink-700)" as unknown as string,
      borderColor: "var(--border-card)" as unknown as string,
      boxShadow: "var(--shadow-button-cream)" as unknown as string,
    },
    hover: { background: "#ffffff" },
  },
  glass: {
    idle: {
      background: "rgba(255,255,255,.12)",
      color: "#fff",
      borderColor: "rgba(255,255,255,.2)",
    },
    hover: { background: "rgba(255,255,255,.22)" },
  },
};

interface CommonProps {
  variant?: Variant;
  children: ReactNode;
  style?: CSSProperties;
}

type ButtonProps = CommonProps &
  ButtonHTMLAttributes<HTMLButtonElement> & { as?: "button" };
type AnchorProps = CommonProps &
  AnchorHTMLAttributes<HTMLAnchorElement> & { as: "a"; href: string };

export default function Button(props: ButtonProps | AnchorProps) {
  const { variant = "dark", children, style, ...rest } = props;
  const [hovered, setHovered] = useState(false);
  const v = variants[variant];
  const combinedStyle: CSSProperties = {
    ...base,
    ...v.idle,
    ...(hovered ? v.hover : {}),
    ...style,
  };

  const handlers = {
    onMouseEnter: () => setHovered(true),
    onMouseLeave: () => setHovered(false),
  };

  if (props.as === "a") {
    const { as: _as, ...anchorRest } = rest as AnchorHTMLAttributes<HTMLAnchorElement> & { as?: string };
    return (
      <a style={combinedStyle} {...handlers} {...anchorRest}>
        {children}
      </a>
    );
  }

  const { as: _as, ...buttonRest } = rest as ButtonHTMLAttributes<HTMLButtonElement> & { as?: string };
  return (
    <button type="button" style={combinedStyle} {...handlers} {...buttonRest}>
      {children}
    </button>
  );
}
