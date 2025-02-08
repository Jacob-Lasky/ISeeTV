import { Channel } from '../models/Channel';
import { ChannelGroup } from '../types/api';
import { Settings } from '../models/Settings';
import { API_URL } from '../config/api';

interface GetChannelsParams {
  search?: string;
  group?: string;
  favoritesOnly?: boolean;
  recentOnly?: boolean;
} 

interface GetChannelsResponse {
  items: Channel[];
  total: number;
  limit: number;
}

interface ProgressCallback {
  (current: number, total: number | { type: 'complete' }): void;
}

interface Program {
  id: string;
  title: string;
  start: Date;
  end: Date;
  duration: number;
}

export const channelService = {
  async getChannels(
    limit?: number,
    params: GetChannelsParams = {}
  ): Promise<GetChannelsResponse> {
    const searchParams = new URLSearchParams({
      ...(limit && { limit: limit.toString() }),
      ...(params.search && { search: params.search }),
      ...(params.favoritesOnly && { favorites_only: 'true' }),
      ...(params.recentOnly && { recent_only: 'true' }),
    });

    console.log('Fetching channels with params:', Object.fromEntries(searchParams.entries()));

    const response = await fetch(`${API_URL}/channels?${searchParams}`);
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Channel fetch error:', errorText);
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    
    // Map the backend fields to frontend fields
    return {
      ...data,
      items: data.items.map((item: any) => ({
        ...item,
        isFavorite: item.is_favorite,
        channel_id: item.channel_id,
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
        channel_id: data.channel_id,
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
                onProgress?.(0, { type: 'complete' });
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
                onProgress?.(0, { type: 'complete' });
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

  async hardReset(): Promise<void> {
    const response = await fetch(`${API_URL}/channels/hard-reset`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to hard reset channels: ${response.statusText}`);
    }

    // Handle the streaming response
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
              console.log('Hard reset progress:', data);
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

  async updateLastWatched(guideId: string): Promise<void> {
    const response = await fetch(`${API_URL}/channels/${guideId}/watched`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to update last watched: ${response.statusText}`);
    }
  },

  async getPrograms(
    channelIds: string[] | null, 
    start: Date, 
    end: Date,
    toTimezone: string | null = null
  ): Promise<Record<string, Program[]>> {
    try {
      const searchParams = new URLSearchParams({
        start: start.toISOString(),
        end: end.toISOString(),
        ...(toTimezone && { to_timezone: toTimezone }),
      });

      if (channelIds) {
        searchParams.append('channel_ids', channelIds.join(','));
      }

      const response = await fetch(`${API_URL}/programs?${searchParams}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch programs: ${response.statusText}`);
      }

      let buffer = '';
      let programData = null;
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            // Decode the chunk and add to buffer
            const chunk = decoder.decode(value, { stream: true });
            buffer += chunk;

            // Split on newlines and process complete lines
            let newlineIndex;
            while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
              const line = buffer.slice(0, newlineIndex).trim();
              buffer = buffer.slice(newlineIndex + 1);

              if (line) {
                try {
                  // Try to parse each complete line
                  const data = JSON.parse(line);
                  if (data.type === 'progress') {
                    console.debug('Progress:', data);
                  } else {
                    programData = data;
                  }
                } catch (e) {
                  // If we can't parse the line, it might be incomplete
                  buffer = line + '\n' + buffer;
                  break;
                }
              }
            }
          }

          // Process any remaining data in buffer
          if (buffer.trim()) {
            try {
              const data = JSON.parse(buffer);
              if (!data.type) {
                programData = data;
              }
            } catch (e) {
              console.warn('Failed to parse final buffer:', buffer);
            }
          }
        } finally {
          reader.releaseLock();
        }
      }

      if (!programData || typeof programData !== 'object') {
        console.error('Invalid program data received:', programData);
        return {};
      }

      console.log('Total programs fetched:', Object.values(programData).flat().length);
      return programData;
    } catch (error) {
      console.error('Failed to fetch programs:', error);
      return {};
    }
  },

  async clearLastWatched(channelId: string): Promise<void> {
    const response = await fetch(`${API_URL}/channels/${channelId}/clear_last_watched`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to clear last watched time');
    }
  },
}; 