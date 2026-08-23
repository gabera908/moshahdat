export type SourceType = "youtube" | "gdrive" | "vimeo" | "dropbox" | "direct" | "embed";
export type VideoStatus = "draft" | "pending" | "published" | "archived";

export interface CategoryBrief {
  id: number;
  name: string;
  slug: string;
}

export interface TagBrief {
  id: number;
  name: string;
  slug: string;
}

export interface VideoListItem {
  id: number;
  title: string;
  slug: string;
  source_type: SourceType;
  embed_url: string | null;
  thumbnail_url: string | null;
  duration: number | null;
  channel_name: string | null;
  views_count: number;
  published_at: string | null;
  created_at: string;
  category: CategoryBrief | null;
  tags: TagBrief[];
  is_featured?: boolean;
}

export interface VideoDetail extends VideoListItem {
  description: string | null;
  source_url: string;
  category_id: number | null;
  status: VideoStatus;
  updated_at: string;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  image_url: string | null;
  sort_order: number;
  is_active: boolean;
  parent_id: number | null;
  created_at: string;
  videos_count?: number;
}

export interface PlaylistSummary {
  id: number;
  title: string;
  slug: string;
  description: string | null;
  thumbnail_url: string | null;
  is_public: boolean;
  created_at: string;
  updated_at: string;
  videos_count?: number;
}

export interface PlaylistDetail extends PlaylistSummary {
  videos: VideoListItem[];
}

export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export interface Paginated<T> {
  items: T[];
  meta: PageMeta;
}
