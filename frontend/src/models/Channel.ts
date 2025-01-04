export interface Channel {
  guide_id: string;
  name: string;
  url: string;
  group: string;
  logo?: string;
  isFavorite?: boolean;
  lastWatched?: Date;
  is_missing: boolean;
} 