import { Settings } from '../models/Settings';

const SETTINGS_KEY = 'iseetv_settings';

const defaultSettings: Settings = {
  m3uUrl: '',
  m3uUpdateInterval: 24,
  epgUrl: '',
  epgUpdateInterval: 24,
  updateOnStart: true,
  theme: 'system',
  recentDays: 3,
  guideStartHour: -2,
  guideEndHour: 12,
  timezone: 'America/New_York',
};

export const settingsService = {
  getSettings: (): Settings => {
    const stored = localStorage.getItem(SETTINGS_KEY);
    return stored ? JSON.parse(stored) : defaultSettings;
  },

  saveSettings: (settings: Settings): void => {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  },

  shouldShowSettings: (): boolean => {
    const settings = settingsService.getSettings();
    return !settings.m3uUrl;
  }
}; 