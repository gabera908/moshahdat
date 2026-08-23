"use client";

import { useQuery } from "@tanstack/react-query";
import { Loader2, Search } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { API_BASE } from "@/lib/api";
import type { Paginated, VideoListItem } from "@/lib/types";

async function fetchSuggestions(q: string): Promise<VideoListItem[]> {
  const res = await fetch(`${API_BASE}/videos?q=${encodeURIComponent(q)}&page_size=6`);
  if (!res.ok) return [];
  const body = await res.json();
  return body?.data?.items ?? [];
}

export default function SearchBox() {
  const router = useRouter();
  const params = useSearchParams();
  const [term, setTerm] = useState(params.get("q") ?? "");
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  const debounced = useDebounce(term.trim(), 300);

  const suggestions = useQuery({
    queryKey: ["suggestions", debounced],
    queryFn: () => fetchSuggestions(debounced),
    enabled: debounced.length >= 2,
  });

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (!boxRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = term.trim();
    setOpen(false);
    router.push(q ? `/search?q=${encodeURIComponent(q)}` : "/search");
  }

  return (
    <div ref={boxRef} className="relative w-full max-w-xl">
      <form onSubmit={submit} role="search">
        <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 shadow-sm transition focus-within:border-primary-400 focus-within:ring-2 focus-within:ring-primary-500/20 dark:border-white/10 dark:bg-surface-card">
          <Search size={18} className="shrink-0 text-slate-400" />
          <input
            type="search"
            value={term}
            onChange={(e) => {
              setTerm(e.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            placeholder="ابحث عن فيديو..."
            aria-label="بحث"
            className="w-full bg-transparent text-sm outline-none placeholder:text-slate-400"
          />
          {suggestions.isFetching && <Loader2 size={16} className="animate-spin text-primary-500" />}
        </div>
      </form>

      {open && debounced.length >= 2 && (
        <div className="absolute inset-x-0 top-full z-50 mt-2 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-card dark:border-white/10 dark:bg-surface-card">
          {suggestions.data && suggestions.data.length > 0 ? (
            <ul className="max-h-80 divide-y divide-slate-100 overflow-auto dark:divide-white/5">
              {suggestions.data.map((v) => (
                <li key={v.id}>
                  <Link
                    href={`/video/${encodeURIComponent(v.slug)}`}
                    onClick={() => setOpen(false)}
                    className="flex items-center gap-3 px-3 py-2.5 transition hover:bg-surface-lightAlt dark:hover:bg-white/5"
                  >
                    <Thumb src={v.thumbnail_url} seed={v.slug} />
                    <span className="line-clamp-2 flex-1 text-sm leading-snug">{v.title}</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-4 py-3 text-sm text-slate-400">لا توجد اقتراحات</p>
          )}
        </div>
      )}
    </div>
  );
}

function Thumb({ src, seed }: { src: string | null; seed: string }) {
  if (src) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt="" className="h-10 w-16 shrink-0 rounded-md object-cover" loading="lazy" />;
  }
  return <span className="h-10 w-16 shrink-0 rounded-md bg-gradient-to-br from-secondary to-primary-700" />;
}

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}
