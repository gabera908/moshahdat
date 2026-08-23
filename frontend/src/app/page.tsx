import { ListVideo, SearchX } from "lucide-react";
import Link from "next/link";

import VideoCard from "@/components/video-card";
import { EmptyState, GridSkeleton, SectionTitle } from "@/components/skeletons";
import {
  getCategories,
  getPlaylists,
  getVideos,
} from "@/lib/api";
import { ar } from "@/lib/i18n/ar";

export const revalidate = 60;

export default async function HomePage() {
  // Parallel fetch; the page must still render if a section is unavailable.
  const [latest, mostViewed, featured, categories, playlists] = await Promise.all([
    getVideos({ sort: "newest", page_size: 8 }).catch(() => null),
    getVideos({ sort: "views", page_size: 4 }).catch(() => null),
    getVideos({ featured: true, page_size: 4 }).catch(() => null),
    getCategories().catch(() => []),
    getPlaylists(1, 4).catch(() => null),
  ]);

  return (
    <div className="space-y-12">
      {/* Hero */}
      <section className="overflow-hidden rounded-3xl bg-gradient-to-l from-secondary via-slate-800 to-primary-900 px-6 py-14 text-center text-white shadow-card sm:px-12">
        <h1 className="text-3xl font-extrabold sm:text-4xl">{ar.home.heroTitle}</h1>
        <p className="mx-auto mt-3 max-w-xl text-sm text-white/70 sm:text-base">
          {ar.home.heroSubtitle}
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/categories"
            className="rounded-full bg-primary-500 px-5 py-2.5 text-sm font-bold shadow-glow transition hover:bg-primary-600"
          >
            {ar.nav.categories}
          </Link>
          <Link
            href="/playlists"
            className="rounded-full border border-white/20 px-5 py-2.5 text-sm font-semibold transition hover:bg-white/10"
          >
            {ar.nav.playlists}
          </Link>
        </div>
      </section>

      {/* Featured */}
      {featured && featured.items.length > 0 && (
        <section>
          <SectionTitle title={ar.home.featured} />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {featured.items.map((v) => (
              <VideoCard key={v.id} video={v} />
            ))}
          </div>
        </section>
      )}

      {/* Latest */}
      <section>
        <SectionTitle
          title={ar.home.latest}
          action={
            <Link href="/search" className="text-sm font-medium text-primary-500 hover:underline">
              {ar.home.viewAll}
            </Link>
          }
        />
        {latest ? <VideosGrid videos={latest.items} /> : <GridSkeleton />}
      </section>

      {/* Most viewed */}
      {mostViewed && mostViewed.items.length > 0 && (
        <section>
          <SectionTitle title={ar.home.mostViewed} />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {mostViewed.items.map((v) => (
              <VideoCard key={v.id} video={v} />
            ))}
          </div>
        </section>
      )}

      {/* Categories */}
      {categories.length > 0 && (
        <section>
          <SectionTitle
            title={ar.home.categories}
            action={
              <Link href="/categories" className="text-sm font-medium text-primary-500 hover:underline">
                {ar.home.viewAll}
              </Link>
            }
          />
          <div className="flex flex-wrap gap-3">
            {categories.map((c) => (
              <Link
                key={c.id}
                href={`/categories/${encodeURIComponent(c.slug)}`}
                className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium transition hover:border-primary-400 hover:text-primary-600 dark:border-white/10 dark:bg-surface-card dark:hover:text-primary-400"
              >
                {c.name}
                {typeof c.videos_count === "number" && (
                  <span className="ms-2 text-xs text-slate-400">({c.videos_count})</span>
                )}
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Playlists */}
      {playlists && playlists.items.length > 0 && (
        <section>
          <SectionTitle
            title={ar.home.playlists}
            action={
              <Link href="/playlists" className="text-sm font-medium text-primary-500 hover:underline">
                {ar.home.viewAll}
              </Link>
            }
          />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {playlists.items.map((p) => (
              <Link
                key={p.id}
                href={`/playlists/${encodeURIComponent(p.slug)}`}
                className="group overflow-hidden rounded-2xl border border-transparent bg-white shadow-sm transition hover:-translate-y-1 hover:border-primary-500/30 hover:shadow-card dark:bg-surface-card"
              >
                <div className="relative aspect-video bg-gradient-to-br from-secondary to-primary-700">
                  {p.thumbnail_url && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={p.thumbnail_url} alt="" loading="lazy" className="h-full w-full object-cover" />
                  )}
                  <span className="absolute bottom-2 right-2 rounded-md bg-black/70 px-2 py-0.5 text-xs font-semibold text-white">
                    {p.videos_count ?? ""} {ar.playlists.videosCount}
                  </span>
                  <span className="absolute inset-0 grid place-items-center opacity-80 transition group-hover:opacity-100">
                    <ListVideo size={30} className="text-white drop-shadow" />
                  </span>
                </div>
                <div className="p-3">
                  <h3 className="line-clamp-1 font-semibold group-hover:text-primary-500">{p.title}</h3>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Backend completely down */}
      {!latest && categories.length === 0 && (
        <EmptyState
          icon={<SearchX size={40} />}
          title={ar.common.error}
          subtitle="تأكد من تشغيل الخادم ثم حدّث الصفحة."
        />
      )}
    </div>
  );
}

function VideosGrid({ videos }: { videos: import("@/lib/types").VideoListItem[] }) {
  if (videos.length === 0) {
    return (
      <EmptyState
        icon={<SearchX size={40} />}
        title="لا توجد فيديوهات منشورة بعد"
        subtitle="أضف فيديوهات من لوحة الإدارة لتظهر هنا."
      />
    );
  }
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {videos.map((v) => (
        <VideoCard key={v.id} video={v} />
      ))}
    </div>
  );
}
