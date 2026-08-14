"use client";

import { useState } from "react";
import type { Audience } from "@/lib/types";

export function TalkingPoints({ points }: { points: Record<Audience, string[]> }) {
  const [audience, setAudience] = useState<Audience>("buyer");
  const list = points[audience];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
          Talking points
        </p>
        <div className="flex rounded-md border border-slate-200 p-0.5 text-xs font-medium">
          {(["buyer", "seller"] as const).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setAudience(option)}
              className={`rounded px-3 py-1 capitalize transition ${
                audience === option
                  ? "bg-brand-500 text-white"
                  : "text-slate-500 hover:text-slate-900"
              }`}
            >
              {option}
            </button>
          ))}
        </div>
      </div>

      {list.length ? (
        <ul className="mt-4 space-y-3">
          {list.map((point, i) => (
            <li key={i} className="flex gap-2 text-sm text-slate-700">
              <span className="mt-0.5 text-brand-500">•</span>
              <span>{point}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-slate-400">
          No talking points generated yet — waiting on first scrape run.
        </p>
      )}
    </div>
  );
}
