import { Channel } from '../models/Channel';
import { ChannelGroup } from '../types/api';
import { Settings } from '../models/Settings';
import { API_URL } from '../config/api';

interface GetChannelsParams {
  search?: string;
  group?: string;
  favoritesOnly?: boolean;
} 

interface GetChannelsResponse {
  items: Channel[];
  total: number;
  skip: number;
  limit: number;
}

interface ProgressCallback {
  (current: number, total: number): void;
}

export const channelService = {
  async getChannels(
    skip: number = 0,
    limit: number = 100,
    params: GetChannelsParams = {}
  ): Promise<GetChannelsResponse> {
    const searchParams = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
      ...(params.search && { search: params.search }),
      ...(params.group && { group: params.group }),
      ...(params.favoritesOnly && { favorites_only: 'true' }),
    });

    const response = await fetch(`${API_URL}/channels?${searchParams}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    
    // Map the backend fields to frontend fields
    return {
      ...data,
      items: data.items.map((item: any) => ({
        ...item,
        isFavorite: item.is_favorite,
        guide_id: item.guide_id,
        lastWatched: item.last_watched ? new Date(item.last_watched) : undefined,
      }))
    };
  },

  async toggleFavorite(guideId: string): Promise<Channel> {
    try {
      const response = await fetch(`${API_URL}/channels/${guideId}/favorite`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to toggle favorite: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        ...data,
        guide_id: data.guide_id,
        isFavorite: data.is_favorite,
        lastWatched: data.last_watched ? new Date(data.last_watched) : undefined,
      };
    } catch (error) {
      console.error('Error toggling favorite:', error);
      throw error;
    }
  },

  async refreshM3U(
    url: string, 
    interval: number, 
    force: boolean = false,
    onProgress?: ProgressCallback
  ): Promise<void> {
    const response = await fetch(
      `${API_URL}/m3u/refresh?url=${encodeURIComponent(url)}&interval=${interval}&force=${force}`, 
      { method: 'POST' }
    );

    if (!response.ok) {
      throw new Error(`Failed to refresh M3U: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (reader) {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (!line) continue;
            try {
              const data = JSON.parse(line);
              if (data.type === 'progress' && onProgress) {
                onProgress(data.current, data.total);
              } else if (data.type === 'complete') {
                // Signal completion with total value
                onProgress?.(100, 100);
              }
            } catch (e) {
              console.warn('Failed to parse line:', line);
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    }
  },

  async refreshEPG(
    url: string, 
    interval: number, 
    force: boolean = false,
    onProgress?: ProgressCallback
  ): Promise<void> {
    const response = await fetch(
      `${API_URL}/epg/refresh?url=${encodeURIComponent(url)}&interval=${interval}&force=${force}`, 
      { method: 'POST' }
    );
    
    if (!response.ok) {
      throw new Error(`Failed to refresh EPG: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (reader) {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (!line) continue;
            try {
              const data = JSON.parse(line);
              if (data.type === 'progress' && onProgress) {
                onProgress(data.current, data.total);
              } else if (data.type === 'complete') {
                // Signal completion with total value
                onProgress?.(100, 100);
              }
            } catch (e) {
              console.warn('Failed to parse line:', line);
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    }
  },

  async getGroups(): Promise<ChannelGroup[]> {
    const response = await fetch(`${API_URL}/channels/groups`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  async saveChannels(channels: Channel[]): Promise<void> {
    const response = await fetch(`${API_URL}/channels/bulk`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(channels),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
  },

  async saveSettings(settings: Settings): Promise<void> {
    const response = await fetch(`${API_URL}/settings/save`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(settings),
    });

    if (!response.ok) {
      throw new Error(`Failed to save settings: ${response.statusText}`);
    }
  },

  async getSettings(): Promise<Settings> {
    const response = await fetch(`${API_URL}/settings`);
    if (!response.ok) {
      throw new Error(`Failed to load settings: ${response.statusText}`);
    }
    return response.json();
  },
}; 