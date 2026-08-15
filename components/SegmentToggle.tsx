import Link from "next/link";
import { PROPERTY_SEGMENTS, type PropertySegment } from "@/lib/types";

/**
 * Property-type switcher. Uses links rather than client-side state so the
 * page can stay a server component and fetch the selected segment's data
 * directly, and so a given view is shareable/bookmarkable by URL.
 */
export function SegmentToggle({
  slug,
  active,
}: {
  slug: string;
  active: PropertySegment;
}) {
  return (
    <div className="flex flex-wrap gap-0.5 rounded-md border border-slate-200 p-0.5 text-xs font-medium dark:border-slate-700">
      {PROPERTY_SEGMENTS.map((segment) => (
        <Link
          key={segment.value}
          href={`/city/${slug}?segment=${segment.value}`}
          scroll={false}
          className={`rounded px-3 py-1 transition ${
            active === segment.value
              ? "bg-brand-500 text-white"
              : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
          }`}
        >
          {segment.label}
        </Link>
      ))}
    </div>
  );
}
