"use client";

import { useEffect, useState } from "react";

import type { SourceType } from "@/lib/types";

interface Props {
  sourceType: SourceType;
  embedUrl: string | null;
  title: string;
}

/** Direct stream endpoint for public Google Drive files (bypasses the iframe). */
function driveStreamUrl(embedUrl: string): string | null {
  const m = embedUrl.match(/\/file\/d\/([A-Za-z0-9_-]{20,})\/preview/);
  if (!m) return null;
  return `https://drive.usercontent.google.com/download?id=${m[1]}&export=download&confirm=t`;
}

function DrivePreviewFrame({ embedUrl, title }: { embedUrl: string; title: string }) {
  return (
    <iframe
      src={embedUrl}
      title={title}
      loading="lazy"
      allow="autoplay"
      allowFullScreen
      referrerPolicy="strict-origin-when-cross-origin"
      className="absolute inset-0 h-full w-full border-0"
    />
  );
}

/**
 * Unified player (plan §12):
 * - direct/dropbox media  -> native HTML5 video
 * - gdrive (public file)  -> try native streaming first; on error fall back
 *                            to Google's preview iframe automatically
 * - everything else       -> iframe embed
 */
export default function VideoPlayer({ sourceType, embedUrl, title }: Props) {
  const [driveFailed, setDriveFailed] = useState(false);
  useEffect(() => setDriveFailed(false), [embedUrl]);

  if (!embedUrl) {
    return (
      <div className="grid aspect-video w-full place-items-center rounded-2xl bg-black text-sm text-white/70">
        لا يتوفر رابط تشغيل لهذا الفيديو
      </div>
    );
  }

  // Google Drive: native stream first, preview iframe as automatic fallback.
  if (sourceType === "gdrive") {
    const stream = driveStreamUrl(embedUrl);
    if (stream && !driveFailed) {
      return (
        <video
          key={stream}
          controls
          playsInline
          preload="metadata"
          onError={() => setDriveFailed(true)}
          className="aspect-video w-full rounded-2xl bg-black"
          src={stream}
        >
          <track kind="captions" />
        </video>
      );
    }
    return (
      <div className="relative aspect-video w-full overflow-hidden rounded-2xl bg-black">
        <DrivePreviewFrame embedUrl={embedUrl} title={title} />
        {driveFailed && (
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-black/80 px-4 py-1.5 text-xs text-white/90">
            يتم التشغيل عبر معاينة Google Drive — إن لم يعمل فتأكد من مشاركة الملف مع «أي شخص لديه الرابط»
          </div>
        )}
      </div>
    );
  }

  const isNative =
    sourceType === "direct" ||
    (sourceType === "dropbox" && /\.(mp4|webm|ogv|ogg|mov|m4v|m3u8)(\?|$)/i.test(embedUrl));

  if (isNative) {
    return (
      <video
        controls
        playsInline
        preload="metadata"
        className="aspect-video w-full rounded-2xl bg-black"
        src={embedUrl}
      >
        <track kind="captions" />
      </video>
    );
  }

  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-2xl bg-black">
      <iframe
        src={embedUrl}
        title={title}
        loading="lazy"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen"
        allowFullScreen
        referrerPolicy="strict-origin-when-cross-origin"
        className="absolute inset-0 h-full w-full border-0"
      />
    </div>
  );
}
