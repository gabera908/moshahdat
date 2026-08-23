import { ArrowRight } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import VideoCard from "@/components/video-card";
import { EmptyState } from "@/components/skeletons";
import { getPlaylistBySlug } from "@/lib/api";

interface Props {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const playlist = await getPlaylistBySlug(slug).catch(() => null);
  if (!playlist) return { title: "قائمة التشغيل غير موجودة" };
  return {
    title: playlist.title,
    description: playlist.description ?? undefined,
    alternates: { canonical: `/playlists/${slug}` },
  };
}

export default async function PlaylistPage({ params }: Props) {
  const { slug } = await params;
  const playlist = await getPlaylistBySlug(slug).catch(() => null);

  if (!playlist) {
    return (
      <EmptyState
        title="قائمة التشغيل غير موجودة"
        subtitle="ربما تكون خاصة أو تم حذفها."
      />
    );
  }

  return (
    <div className="space-y-6">
      <Link
        href="/playlists"
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 transition hover:text-primary-500 dark:text-slate-400"
      >
        <ArrowRight size={15} />
        كل قوائم التشغيل
      </Link>

      <header className="overflow-hidden rounded-3xl bg-gradient-to-l from-secondary via-slate-800 to-primary-900 p-8 text-white shadow-card">
        <p className="text-xs font-semibold uppercase tracking-wider text-white/60">قائمة تشغيل</p>
        <h1 className="mt-1 text-2xl font-extrabold sm:text-3xl">{playlist.title}</h1>
        {playlist.description && (
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-white/70">{playlist.description}</p>
        )}
        <span className="mt-3 inline-block rounded-full bg-white/10 px-3 py-1 text-xs font-semibold">
          {playlist.videos.length} فيديو
        </span>
      </header>

      {playlist.videos.length === 0 ? (
        <EmptyState title="لا توجد فيديوهات في هذه القائمة بعد" />
      ) : (
        <ol className="space-y-4">
          {playlist.videos.map((video, index) => (
            <li key={video.id} className="flex items-start gap-3">
              <span className="mt-1 hidden w-7 shrink-0 rounded-lg bg-slate-100 py-1.5 text-center text-sm font-bold text-slate-500 dark:bg-white/5 dark:text-slate-400 sm:block">
                {index + 1}
              </span>
              <VideoCard video={video} className="flex-1" />
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
