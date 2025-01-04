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

  async refreshM3U(url: string, interval: number, force: boolean = false): Promise<void> {
    const response = await fetch(
      `${API_URL}/m3u/refresh?url=${encodeURIComponent(url)}&interval=${interval}&force=${force}`, 
      { method: 'POST' }
    );
    
    if (!response.ok) {
      throw new Error(`Failed to refresh M3U: ${response.statusText}`);
    }
  },

  async refreshEPG(url: string, interval: number, force: boolean = false): Promise<void> {
    const response = await fetch(
      `${API_URL}/epg/refresh?url=${encodeURIComponent(url)}&interval=${interval}&force=${force}`, 
      { method: 'POST' }
    );
    
    if (!response.ok) {
      throw new Error(`Failed to refresh EPG: ${response.statusText}`);
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