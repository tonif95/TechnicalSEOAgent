export interface SEOResult {
  id: number;
  url: string;
  status_code: number;
  title_tag: string;
  meta_description: string;
  h1_count: number;
  h2_count: number;
  h3_count: number;
  internal_links: number;
  external_links: number;
  image_count: number;
  images_without_alt: number;
  word_count: number;
  load_time: number;
  mobile_friendly: boolean;
  has_schema: boolean;
  canonical_url: string;
  created_at: string;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}