import { Channel } from '../models/Channel';

const STORAGE_KEY = 'recentChannels';
const MAX_RECENT_CHANNELS = 10;
const MAX_AGE_MS = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

interface RecentChannel extends Channel {
  timestamp: number;
}

export const recentChannelsService = {
  getRecentChannels(): Channel[] {
    try {
      const now = Date.now();
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) return [];

      const recentChannels: RecentChannel[] = JSON.parse(stored);
      
      // Filter out old channels and convert to Channel type
      return recentChannels
        .filter(ch => (now - ch.timestamp) <= MAX_AGE_MS)
        .map(({ timestamp, ...channel }) => channel);

    } catch (error) {
      console.error('Error getting recent channels:', error);
      return [];
    }
  },

  addRecentChannel(channel: Channel) {
    try {
      const now = Date.now();
      const stored = localStorage.getItem(STORAGE_KEY);
      const recentChannels: RecentChannel[] = stored ? JSON.parse(stored) : [];
      
      const filtered = recentChannels
        .filter(ch => (now - ch.timestamp) <= MAX_AGE_MS)
        .filter(ch => ch.guide_id !== channel.guide_id);
      
      // Add new channel
      const updated: RecentChannel[] = [
        { ...channel, timestamp: now },
        ...filtered
      ].slice(0, MAX_RECENT_CHANNELS);
      
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    } catch (error) {
      console.error('Error adding recent channel:', error);
    }
  }
}; 