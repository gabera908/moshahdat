import type { MetadataRoute } from "next";

import { API_BASE_SERVER, SITE_URL } from "@/lib/api";

interface SlugItem {
  slug: string;
  updated?: string;
}

async function fetchSlugs(path: string): Promise<SlugItem[]> {
  try {
    const res = await fetch(`${API_BASE_SERVER}${path}`, { cache: "no-store" });
    if (!res.ok) return [];
    const body = await res.json();
    return body?.data?.items ?? body?.data ?? [];
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [videos, categories, playlists] = await Promise.all([
    fetchSlugs("/videos?page_size=100&sort=newest"),
    fetchSlugs("/categories"),
    fetchSlugs("/playlists?page_size=100"),
  ]);

  const staticRoutes: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/`, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/search`, changeFrequency: "daily", priority: 0.6 },
    { url: `${SITE_URL}/categories`, changeFrequency: "weekly", priority: 0.7 },
    { url: `${SITE_URL}/playlists`, changeFrequency: "weekly", priority: 0.7 },
  ];

  return [
    ...staticRoutes,
    ...videos.map((v) => ({
      url: `${SITE_URL}/video/${encodeURIComponent(v.slug)}`,
      lastModified: v.updated ? new Date(v.updated) : undefined,
      changeFrequency: "monthly" as const,
      priority: 0.9,
    })),
    ...categories.map((c) => ({
      url: `${SITE_URL}/categories/${encodeURIComponent(c.slug)}`,
      changeFrequency: "weekly" as const,
      priority: 0.6,
    })),
    ...playlists.map((p) => ({
      url: `${SITE_URL}/playlists/${encodeURIComponent(p.slug)}`,
      changeFrequency: "weekly" as const,
      priority: 0.6,
    })),
  ];
}
