import { Settings } from "../models/Settings";
import { getUserTimezone } from "../utils/dateUtils";
const SETTINGS_KEY = "iseetv_settings";

export const defaultSettings: Settings = {
  m3uUrl: "",
  m3uUpdateInterval: 12,
  epgUrl: "",
  epgUpdateInterval: 12,
  updateOnStart: true,
  theme: "system",
  recentDays: 3,
  guideStartHour: -2,
  guideEndHour: 12,
  timezone: getUserTimezone(),
  use24Hour: true,
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
  },
};
