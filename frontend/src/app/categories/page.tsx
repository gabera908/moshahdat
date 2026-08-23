import { ChevronLeft, FolderOpen } from "lucide-react";
import Link from "next/link";

import { EmptyState, SectionTitle } from "@/components/skeletons";
import { getCategories } from "@/lib/api";
import { ar } from "@/lib/i18n/ar";
import type { Category } from "@/lib/types";

export const metadata = {
  title: "التصنيفات",
  description: "تصفح جميع تصنيفات الفيديوهات",
};

function CategoryCard({ cat, count }: { cat: Category; count?: number }) {
  return (
    <Link
      href={`/categories/${encodeURIComponent(cat.slug)}`}
      className="group overflow-hidden rounded-2xl bg-white shadow-sm transition hover:-translate-y-1 hover:shadow-card dark:bg-surface-card"
    >
      <div className={`h-20 bg-gradient-to-br ${cat.slug.length % 2 ? "from-secondary to-primary-700" : "from-primary-700 to-secondary"}`} />
      <div className="p-4">
        <h3 className="font-bold transition group-hover:text-primary-500">{cat.name}</h3>
        {cat.description && (
          <p className="mt-1 line-clamp-2 text-sm text-slate-500 dark:text-slate-400">
            {cat.description}
          </p>
        )}
        {typeof count === "number" && (
          <span className="mt-2 inline-block text-xs text-slate-400">
            {count} {ar.categories.videosCount}
          </span>
        )}
      </div>
    </Link>
  );
}

export default async function CategoriesPage() {
  const categories = await getCategories().catch(() => []);

  const byId = new Map(categories.map((c) => [c.id, c]));
  const childrenOf = new Map<number | null, Category[]>();
  for (const c of categories) {
    // A child whose parent is missing (deleted) is treated as a root.
    const key = c.parent_id && byId.has(c.parent_id) ? c.parent_id : null;
    const list = childrenOf.get(key) ?? [];
    list.push(c);
    childrenOf.set(key, list);
  }
  const roots = childrenOf.get(null) ?? [];

  return (
    <div className="space-y-8">
      <SectionTitle title={ar.categories.title} />

      {categories.length === 0 ? (
        <EmptyState icon={<FolderOpen size={40} />} title={ar.categories.empty} />
      ) : (
        roots.map((root) => {
          const kids = childrenOf.get(root.id) ?? [];
          return (
            <section key={root.id}>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <CategoryCard cat={root} count={root.videos_count} />
              </div>

              {kids.length > 0 && (
                <div className="mt-3 space-y-1.5 border-s-2 border-primary-500/30 ps-4">
                  {kids.map((kid) => {
                    const grandKids = childrenOf.get(kid.id) ?? [];
                    return (
                      <div key={kid.id}>
                        <Link
                          href={`/categories/${encodeURIComponent(kid.slug)}`}
                          className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-white hover:text-primary-600 dark:text-slate-300 dark:hover:bg-surface-card dark:hover:text-primary-400"
                        >
                          <ChevronLeft size={14} className="text-primary-500" />
                          {kid.name}
                          <span className="text-xs text-slate-400">({kid.videos_count ?? 0})</span>
                        </Link>
                        {grandKids.length > 0 && (
                          <div className="ms-6 flex flex-wrap gap-x-4">
                            {grandKids.map((gk) => (
                              <Link
                                key={gk.id}
                                href={`/categories/${encodeURIComponent(gk.slug)}`}
                                className="py-0.5 text-xs text-slate-500 hover:text-primary-500 dark:text-slate-400"
                              >
                                • {gk.name}
                              </Link>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          );
        })
      )}
    </div>
  );
}
