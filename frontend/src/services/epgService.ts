import { API_URL } from '../config/api';

class EPGService {
  async refreshEPG(url: string): Promise<void> {
    try {
      const response = await fetch(`${API_URL}/epg/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.error('Failed to refresh EPG:', error);
      throw error;
    }
  }
}

export const epgService = new EPGService();
