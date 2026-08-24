"use client";

import { useState } from "react";

const ITEMS = [
  {
    q: "Does this need live access to my AWS account?",
    a: "No. CSV upload only — there's no live billing API integration, no IAM role to grant, no read access to your account. You export a billing CSV when you want an audit and upload it. Nothing runs against your infrastructure.",
  },
  {
    q: "What happens to tier-1 essential services?",
    a: "Dropped from recommendations entirely. You mark them tier-1 during setup; the conflict resolver removes them before ranking, so they never appear in a ticket. Protected means untouched.",
  },
  {
    q: "What if a recommendation is actually risky?",
    a: "It's flagged as conflicted and surfaced, not hidden. Any tier-2 touch or risk step-up gets marked with its reason and forced to the bottom of the ranked list. You decide — the tool never quietly buries a risky change.",
  },
  {
    q: "How is my data secured?",
    a: "Row-level security on every table, scoped to your user id. Backend writes still independently verify ownership per request, and a mismatch returns 404 — a request can't even tell whether someone else's row exists. Single-tenant throughout.",
  },
  {
    q: "Do reports expire?",
    a: "Yes — 30-day retention. A nightly job hard-deletes anything past its expiry, and soft-delete is available anytime you want a report gone sooner. The PDF export stays downloadable across that window.",
  },
];

export default function Faq() {
  const [open, setOpen] = useState<Record<number, boolean>>({ 0: true });
  const toggle = (i: number) => setOpen((s) => ({ ...s, [i]: !s[i] }));

  return (
    <div style={{ borderTop: "1px solid var(--border-hairline)" }}>
      {ITEMS.map((item, i) => {
        const isOpen = !!open[i];
        return (
          <div className="l-faq-row" key={item.q}>
            <button
              className="l-faq-q"
              onClick={() => toggle(i)}
              aria-expanded={isOpen}
            >
              <span style={{ flex: 1 }}>{item.q}</span>
              <span
                className="l-faq-icon"
                style={{ transform: isOpen ? "rotate(180deg)" : "rotate(0deg)" }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </span>
            </button>
            <div
              className="l-faq-a"
              style={{ maxHeight: isOpen ? 260 : 0, opacity: isOpen ? 1 : 0 }}
            >
              <p>{item.a}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
