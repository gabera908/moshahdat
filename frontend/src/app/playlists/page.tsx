import { ListVideo } from "lucide-react";
import Link from "next/link";

import { EmptyState, SectionTitle } from "@/components/skeletons";
import { getPlaylists } from "@/lib/api";
import { ar } from "@/lib/i18n/ar";

export const metadata = {
  title: "قوائم التشغيل",
  description: "تصفح قوائم التشغيل المنظمة",
};

export default async function PlaylistsPage() {
  const playlists = await getPlaylists(1, 24).catch(() => null);

  return (
    <div className="space-y-6">
      <SectionTitle title={ar.playlists.title} />

      {!playlists || playlists.items.length === 0 ? (
        <EmptyState icon={<ListVideo size={40} />} title={ar.playlists.empty} />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {playlists.items.map((p) => (
            <Link
              key={p.id}
              href={`/playlists/${encodeURIComponent(p.slug)}`}
              className="group overflow-hidden rounded-2xl border border-transparent bg-white shadow-sm transition hover:-translate-y-1 hover:border-primary-500/30 hover:shadow-card dark:bg-surface-card"
            >
              <div className="relative aspect-video bg-gradient-to-br from-secondary to-primary-700">
                {p.thumbnail_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={p.thumbnail_url}
                    alt=""
                    loading="lazy"
                    className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                  />
                )}
                <span className="absolute inset-0 grid place-items-center opacity-70 transition group-hover:opacity-100">
                  <ListVideo size={32} className="text-white drop-shadow" />
                </span>
                {typeof p.videos_count === "number" && (
                  <span className="absolute bottom-2 left-2 rounded-md bg-black/75 px-2 py-0.5 text-xs font-semibold text-white">
                    {p.videos_count} {ar.playlists.videosCount}
                  </span>
                )}
              </div>
              <div className="p-4">
                <h3 className="line-clamp-1 font-bold transition group-hover:text-primary-500">
                  {p.title}
                </h3>
                {p.description && (
                  <p className="mt-1 line-clamp-2 text-sm text-slate-500 dark:text-slate-400">
                    {p.description}
                  </p>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
