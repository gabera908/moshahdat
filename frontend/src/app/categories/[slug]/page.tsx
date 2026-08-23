import { ArrowRight } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import VideoCard from "@/components/video-card";
import { EmptyState, PaginationLinks, SectionTitle } from "@/components/skeletons";
import { getCategories, getVideos } from "@/lib/api";

interface Props {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string }>;
}

async function findCategory(slug: string) {
  const categories = await getCategories().catch(() => []);
  return categories.find((c) => c.slug === slug) ?? null;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug: rawSlug } = await params;
  // App Router passes dynamic params URL-encoded — decode before use.
  const slug = decodeURIComponent(rawSlug);
  const cat = await findCategory(slug);
  if (!cat) return { title: "التصنيف غير موجود" };
  return {
    title: cat.name,
    description: cat.description ?? `فيديوهات تصنيف ${cat.name}`,
    alternates: { canonical: `/categories/${slug}` },
  };
}

export default async function CategoryPage({ params, searchParams }: Props) {
  const [{ slug }, sp] = await Promise.all([params, searchParams]);
  const page = Math.max(1, parseInt(sp.page ?? "1", 10) || 1);

  const [category, results] = await Promise.all([
    findCategory(slug),
    getVideos({ category: slug, page, page_size: 12 }).catch(() => null),
  ]);

  return (
    <div className="space-y-6">
      <Link
        href="/categories"
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 transition hover:text-primary-500 dark:text-slate-400"
      >
        <ArrowRight size={15} />
        كل التصنيفات
      </Link>

      <SectionTitle title={category?.name ?? "التصنيف"} />

      {results && results.items.length > 0 ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {results.items.map((v) => (
              <VideoCard key={v.id} video={v} />
            ))}
          </div>
          <PaginationLinks
            page={page}
            pages={results.meta.pages}
            buildHref={(p) => `/categories/${encodeURIComponent(slug)}?page=${p}`}
          />
        </>
      ) : (
        <EmptyState
          title="لا توجد فيديوهات في هذا التصنيف بعد"
          subtitle="سيظهر المحتوى هنا عند نشره."
        />
      )}
    </div>
  );
}
