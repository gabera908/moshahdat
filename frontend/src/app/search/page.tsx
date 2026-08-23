import { SearchX } from "lucide-react";
import Link from "next/link";

import VideoCard from "@/components/video-card";
import { EmptyState, PaginationLinks, SectionTitle } from "@/components/skeletons";
import { getCategories, getVideos } from "@/lib/api";
import { ar } from "@/lib/i18n/ar";

interface Props {
  searchParams: Promise<{
    q?: string;
    category?: string;
    sort?: string;
    page?: string;
  }>;
}

const SORTS = [
  { key: "newest", label: "الأحدث" },
  { key: "views", label: "الأكثر مشاهدة" },
  { key: "oldest", label: "الأقدم" },
  { key: "title", label: "أبجديًا" },
] as const;

export const metadata = { title: "البحث" };

function buildQuery(base: Record<string, string | undefined>, overrides: Record<string, string>) {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries({ ...base, ...overrides })) {
    if (v) sp.set(k, v);
  }
  return `/search?${sp.toString()}`;
}

export default async function SearchPage({ searchParams }: Props) {
  const sp = await searchParams;
  const q = sp.q?.trim() ?? "";
  const category = sp.category ?? "";
  const sort = (sp.sort as "newest" | "oldest" | "views" | "title") ?? "newest";
  const page = Math.max(1, parseInt(sp.page ?? "1", 10) || 1);

  const [categories, results] = await Promise.all([
    getCategories().catch(() => []),
    getVideos({
      q: q || undefined,
      category: category || undefined,
      sort,
      page,
      page_size: 12,
    }).catch(() => null),
  ]);

  const base = { q, category, sort, page: undefined as string | undefined };
  const hasFilters = Boolean(q || category);

  return (
    <div className="space-y-6">
      <SectionTitle title={q ? `${ar.search.resultsFor}: "${q}"` : ar.nav.latest} />

      {/* Filters */}
      <form
        action="/search"
        method="get"
        className="flex flex-wrap items-center gap-3 rounded-2xl bg-white p-4 shadow-sm dark:bg-surface-card"
      >
        <input type="hidden" name="q" value={q} />
        <select
          name="category"
          defaultValue={category}
          aria-label={ar.search.filterCategory}
          className="rounded-lg border border-slate-200 bg-transparent px-3 py-2 text-sm dark:border-white/10 dark:bg-surface-dark"
        >
          <option value="">{ar.common.all}</option>
          {categories.map((c) => (
            <option key={c.id} value={c.slug}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          name="sort"
          defaultValue={sort}
          aria-label="الترتيب"
          className="rounded-lg border border-slate-200 bg-transparent px-3 py-2 text-sm dark:border-white/10 dark:bg-surface-dark"
        >
          {SORTS.map((s) => (
            <option key={s.key} value={s.key}>
              {s.label}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="rounded-lg bg-primary-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary-600"
        >
          تطبيق
        </button>
      </form>

      {results && results.items.length > 0 ? (
        <>
          <p className="text-sm text-slate-400">
            {results.meta.total} نتيجة — صفحة {results.meta.page} من {results.meta.pages}
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {results.items.map((v) => (
              <VideoCard key={v.id} video={v} />
            ))}
          </div>
          <PaginationLinks
            page={page}
            pages={results.meta.pages}
            buildHref={(p) => buildQuery(base, { page: String(p) })}
          />
        </>
      ) : (
        <EmptyState
          icon={<SearchX size={40} />}
          title={hasFilters ? ar.search.noResults : "لا توجد فيديوهات بعد"}
          subtitle={
            hasFilters
              ? ar.search.tryDifferent
              : "سيظهر المحتوى هنا بعد إضافته من لوحة الإدارة."
          }
        />
      )}
    </div>
  );
}
