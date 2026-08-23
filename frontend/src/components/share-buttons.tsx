"use client";

import { Check, Copy, Facebook, Link2, Send, Twitter } from "lucide-react";
import { useState } from "react";

interface Props {
  url: string;
  title: string;
}

export default function ShareButtons({ url, title }: Props) {
  const [copied, setCopied] = useState(false);
  const encodedUrl = encodeURIComponent(url);
  const encodedTitle = encodeURIComponent(title);

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // Fallback for older browsers
      const ta = document.createElement("textarea");
      ta.value = url;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const btn =
    "inline-flex items-center gap-1.5 rounded-full px-3.5 py-2 text-xs font-semibold text-white transition hover:brightness-110";

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" onClick={copy} className={`${btn} bg-secondary hover:bg-slate-600`}>
        {copied ? <Check size={14} /> : <Copy size={14} />}
        {copied ? "تم النسخ" : "نسخ الرابط"}
      </button>
      <a
        href={`https://wa.me/?text=${encodedTitle}%20${encodedUrl}`}
        target="_blank"
        rel="noopener noreferrer"
        className={`${btn} bg-[#25D366]`}
      >
        واتساب
      </a>
      <a
        href={`https://t.me/share/url?url=${encodedUrl}&text=${encodedTitle}`}
        target="_blank"
        rel="noopener noreferrer"
        className={`${btn} bg-[#229ED9]`}
      >
        <Send size={13} /> تيليجرام
      </a>
      <a
        href={`https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}`}
        target="_blank"
        rel="noopener noreferrer"
        className={`${btn} bg-black`}
      >
        <Twitter size={13} /> X
      </a>
      <a
        href={`https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`}
        target="_blank"
        rel="noopener noreferrer"
        className={`${btn} bg-[#1877F2]`}
      >
        <Facebook size={13} /> فيسبوك
      </a>
    </div>
  );
}
