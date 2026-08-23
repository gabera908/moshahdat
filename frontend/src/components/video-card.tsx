import { Eye } from "lucide-react";
import Link from "next/link";

import type { VideoListItem } from "@/lib/types";
import { ar } from "@/lib/i18n/ar";
import { cn, formatDuration, formatDate, formatViews, thumbGradient } from "@/lib/utils";

interface Props {
  video: VideoListItem;
  className?: string;
}

export default function VideoCard({ video, className }: Props) {
  const duration = formatDuration(video.duration);

  return (
    <Link
      href={`/video/${encodeURIComponent(video.slug)}`}
      className={cn(
        "group block overflow-hidden rounded-2xl border border-transparent bg-white shadow-sm transition-all duration-200",
        "hover:-translate-y-1 hover:border-primary-500/30 hover:shadow-card dark:bg-surface-card",
        className,
      )}
    >
      <div
        className={cn(
          "relative aspect-video overflow-hidden bg-gradient-to-br",
          thumbGradient(video.slug),
        )}
      >
        {video.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={video.thumbnail_url}
            alt={video.title}
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <span className="grid h-full w-full place-items-center text-3xl font-black text-white/20">
            ▶
          </span>
        )}
        {duration && (
          <span className="absolute bottom-2 left-2 rounded-md bg-black/80 px-1.5 py-0.5 text-[11px] font-semibold tabular-nums text-white">
            {duration}
          </span>
        )}
      </div>

      <div className="p-3">
        {video.channel_name && (
          <p className="mb-1 line-clamp-1 text-[11px] font-medium text-primary-600/90 dark:text-primary-400/90">
            {video.channel_name}
          </p>
        )}
        <h3 className="line-clamp-2 min-h-[2.6rem] text-sm font-semibold leading-snug transition group-hover:text-primary-500">
          {video.title}
        </h3>
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
          <span className="inline-flex items-center gap-1">
            <Eye size={13} />
            {formatViews(video.views_count)} {ar.video.views}
          </span>
          <span>{formatDate(video.published_at ?? video.created_at)}</span>
          {video.category && (
            <span className="rounded-full bg-primary-500/10 px-2 py-0.5 font-medium text-primary-600 dark:text-primary-400">
              {video.category.name}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
