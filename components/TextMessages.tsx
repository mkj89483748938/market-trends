"use client";

import { useState } from "react";
import type { Audience } from "@/lib/types";

/**
 * Suggested follow-up texts, with a copy button per message — these exist to
 * be sent, so the useful action is "get this into my phone", not "read it".
 */
export function TextMessages({ messages }: { messages: Record<Audience, string[]> }) {
  const [audience, setAudience] = useState<Audience>("buyer");
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const list = messages[audience];

  // Nothing to show for cities outside the pilot — render nothing rather than
  // an empty card implying something failed.
  if (!messages.buyer.length && !messages.seller.length) return null;

  async function copy(text: string, index: number) {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 1500);
    } catch {
      // Clipboard access can be denied (insecure context, permissions).
      // The text is selectable on screen, so this is a convenience, not the
      // only way to get it.
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Follow-up texts
          </p>
          <p className="mt-0.5 text-xs text-slate-400 dark:text-slate-500">
            Replace {"{first_name}"} before sending
          </p>
        </div>
        <div className="flex rounded-md border border-slate-200 p-0.5 text-xs font-medium dark:border-slate-700">
          {(["buyer", "seller"] as const).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setAudience(option)}
              className={`rounded px-3 py-1 capitalize transition ${
                audience === option
                  ? "bg-brand-500 text-white"
                  : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
              }`}
            >
              {option}
            </button>
          ))}
        </div>
      </div>

      {list.length ? (
        <ul className="mt-4 space-y-3">
          {list.map((message, i) => (
            <li
              key={i}
              className="rounded-lg border border-slate-100 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-900"
            >
              <p className="text-sm text-slate-700 dark:text-slate-300">{message}</p>
              <div className="mt-2 flex items-center justify-between">
                <span className="text-xs text-slate-400 dark:text-slate-500">
                  {message.length} characters
                </span>
                <button
                  type="button"
                  onClick={() => copy(message, i)}
                  className="rounded border border-slate-200 px-2 py-0.5 text-xs font-medium text-slate-600 transition hover:border-brand-500 hover:text-brand-600 dark:border-slate-600 dark:text-slate-300 dark:hover:border-brand-500"
                >
                  {copiedIndex === i ? "Copied" : "Copy"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-slate-400 dark:text-slate-500">
          No {audience} texts for this city yet.
        </p>
      )}
    </div>
  );
}
