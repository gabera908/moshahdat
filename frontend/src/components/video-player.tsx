import type { SourceType } from "@/lib/types";

interface Props {
  sourceType: SourceType;
  embedUrl: string | null;
  title: string;
}

/**
 * Unified player: picks iframe embed vs native HTML5 video based on the
 * provider-detected playback mode. External videos are never downloaded.
 */
export default function VideoPlayer({ sourceType, embedUrl, title }: Props) {
  if (!embedUrl) {
    return (
      <div className="grid aspect-video w-full place-items-center rounded-2xl bg-black text-sm text-white/70">
        لا يتوفر رابط تشغيل لهذا الفيديو
      </div>
    );
  }

  const isNative =
    (sourceType === "direct") ||
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
