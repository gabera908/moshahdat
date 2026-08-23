import type {
  Category,
  Paginated,
  PlaylistDetail,
  PlaylistSummary,
  VideoDetail,
  VideoListItem,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:6688/api/v1";
export const SITE_NAME = process.env.NEXT_PUBLIC_SITE_NAME ?? "منصة الفيديو";
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:6688";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public errorCode?: string,
  ) {
    super(message);
  }
}

interface Envelope<T> {
  success: boolean;
  message?: string;
  error_code?: string;
  data?: T;
}

async function request<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  } catch {
    throw new ApiError("تعذر الاتصال بالخادم", 0, "NETWORK_ERROR");
  }

  let body: Envelope<T> | null = null;
  try {
    body = (await res.json()) as Envelope<T>;
  } catch {
    /* non-JSON response */
  }

  if (!res.ok || !body?.success) {
    throw new ApiError(
      body?.message ?? "حدث خطأ غير متوقع",
      res.status,
      body?.error_code,
    );
  }
  return body.data as T;
}

/** Safe variant: returns null instead of throwing (for optional sections). */
export async function safeRequest<T>(path: string): Promise<T | null> {
  try {
    return await request<T>(path);
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------- videos

export async function getVideos(params: {
  q?: string;
  category?: string;
  tag?: string;
  sort?: "newest" | "oldest" | "views" | "title";
  page?: number;
  page_size?: number;
  featured?: boolean;
}): Promise<Paginated<VideoListItem>> {
  const sp = new URLSearchParams();
  if (params.q) sp.set("q", params.q);
  if (params.category) sp.set("category", params.category);
  if (params.tag) sp.set("tag", params.tag);
  if (params.sort) sp.set("sort", params.sort);
  sp.set("page", String(params.page ?? 1));
  sp.set("page_size", String(params.page_size ?? 12));
  if (params.featured !== undefined) sp.set("featured", String(params.featured));
  return request(`/videos?${sp.toString()}`);
}

export async function getVideoBySlug(slug: string): Promise<VideoDetail> {
  return request(`/videos/slug/${encodeURIComponent(slug)}`);
}

export async function getRelatedVideos(
  slug: string,
  categoryId: number | null,
): Promise<Paginated<VideoListItem>> {
  const cat = categoryId ? `&category=${categoryId}` : "";
  return request(`/videos?page_size=12&sort=newest${cat}`);
}

// ---------------------------------------------------------------- categories

export async function getCategories(): Promise<Category[]> {
  const data = await request<{ items: Category[] }>("/categories");
  return data.items;
}

// ---------------------------------------------------------------- playlists

export async function getPlaylists(page = 1, pageSize = 12): Promise<Paginated<PlaylistSummary>> {
  return request(`/playlists?page=${page}&page_size=${pageSize}`);
}

export async function getPlaylistBySlug(slug: string): Promise<PlaylistDetail> {
  return request(`/playlists/slug/${encodeURIComponent(slug)}`);
}
