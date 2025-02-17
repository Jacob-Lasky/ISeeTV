export interface Channel {
  channel_id: string;
  name: string;
  url: string;
  group: string;
  logo?: string;
  isFavorite: boolean;
  source?: string;
  lastWatched?: Date;
  is_missing: boolean;
}

export interface ChannelResponse {
  items: Channel[];
  total: number;
  skip: number;
  limit: number;
}
