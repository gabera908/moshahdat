import { ArrowRight, ExternalLink, Eye, ListVideo } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import ShareButtons from "@/components/share-buttons";
import VideoCard from "@/components/video-card";
import VideoPlayer from "@/components/video-player";
import ViewTracker from "@/components/view-tracker";
import { getRelatedVideos, getVideoBySlug, SITE_NAME, SITE_URL } from "@/lib/api";
import { ar } from "@/lib/i18n/ar";
import { formatDate, formatViews } from "@/lib/utils";

interface Props {
  params: Promise<{ slug: string }>;
}

export const revalidate = 30;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  try {
    const video = await getVideoBySlug(slug);
    const url = `${SITE_URL}/video/${slug}`;
    return {
      title: video.title,
      description: video.description ?? undefined,
      alternates: { canonical: url },
      openGraph: {
        title: video.title,
        description: video.description ?? "",
        url,
        type: "video.other",
        images: video.thumbnail_url ? [{ url: video.thumbnail_url }] : undefined,
      },
      twitter: {
        card: "summary_large_image",
        title: video.title,
        description: video.description ?? undefined,
        images: video.thumbnail_url ? [video.thumbnail_url] : undefined,
      },
    };
  } catch {
    return { title: ar.video.notFound };
  }
}

export default async function WatchPage({ params }: Props) {
  const { slug } = await params;

  let video;
  try {
    video = await getVideoBySlug(slug);
  } catch {
    notFound();
  }

  const related = await getRelatedVideos(video.slug, video.category?.id ?? null).catch(() => null);
  const relatedItems = (related?.items ?? []).filter((v) => v.id !== video.id).slice(0, 8);
  const canonicalUrl = `${SITE_URL}/video/${video.slug}`;

  // JSON-LD structured data (plan §25)
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "VideoObject",
    name: video.title,
    description: video.description ?? undefined,
    thumbnailUrl: video.thumbnail_url ?? undefined,
    uploadDate: video.published_at ?? video.created_at,
    embedUrl: video.embed_url ?? undefined,
    interactionStatistic: {
      "@type": "InteractionCounter",
      interactionType: { "@type": "WatchAction" },
      userInteractionCount: video.views_count,
    },
  };

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_340px]">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <ViewTracker videoId={video.id} />

      <div className="min-w-0 space-y-4">
        <VideoPlayer
          sourceType={video.source_type}
          embedUrl={video.embed_url}
          title={video.title}
        />

        <h1 className="text-xl font-bold leading-snug sm:text-2xl">{video.title}</h1>

        {video.channel_name && (
          <p className="text-sm font-semibold text-primary-600 dark:text-primary-400">
            📺 {video.channel_name}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-slate-500 dark:text-slate-400">
          <span className="inline-flex items-center gap-1.5 font-medium text-primary-600 dark:text-primary-400">
            <Eye size={15} />
            {formatViews(video.views_count)} {ar.video.views}
          </span>
          <span>
            {ar.video.publishedOn} {formatDate(video.published_at ?? video.created_at)}
          </span>
          {video.category && (
            <Link
              href={`/categories/${encodeURIComponent(video.category.slug)}`}
              className="rounded-full bg-primary-500/10 px-3 py-1 text-xs font-semibold text-primary-600 transition hover:bg-primary-500/20 dark:text-primary-400"
            >
              {video.category.name}
            </Link>
          )}
        </div>

        <ShareButtons url={canonicalUrl} title={video.title} />

        {video.description && (
          <section className="rounded-2xl bg-white p-5 shadow-sm dark:bg-surface-card">
            <h2 className="mb-2 text-sm font-bold">{ar.video.description}</h2>
            <p className="whitespace-pre-line text-sm leading-relaxed text-slate-700 dark:text-slate-300">
              {video.description}
            </p>
          </section>
        )}

        {video.tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {video.tags.map((t) => (
              <Link
                key={t.id}
                href={`/search?q=${encodeURIComponent(t.name)}`}
                className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-500 transition hover:border-primary-400 hover:text-primary-500 dark:border-white/10 dark:text-slate-400"
              >
                #{t.name}
              </Link>
            ))}
          </div>
        )}

        {(video.source_type === "embed" || video.source_type === "dropbox") && (
          <a
            href={video.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-primary-500"
          >
            <ExternalLink size={13} />
            {ar.video.openOriginal}
          </a>
        )}
      </div>

      {/* Sidebar: related videos */}
      <aside className="space-y-4">
        <h2 className="flex items-center gap-2 text-base font-bold">
          <span className="h-5 w-1.5 rounded-full bg-gradient-to-b from-primary-400 to-primary-600" />
          {ar.video.related}
        </h2>
        {relatedItems.length > 0 ? (
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-1">
            {relatedItems.map((v) => (
              <VideoCard key={v.id} video={v} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-400">لا توجد فيديوهات ذات صلة</p>
        )}
      </aside>
    </div>
  );
}
