export interface Settings {
  m3uUrl: string;
  m3uUpdateInterval: number;
  epgUrl: string;
  epgUpdateInterval: number;
  updateOnStart: boolean;
  theme: "light" | "dark" | "system";
  recentDays: number;
  guideStartHour: number;
  guideEndHour: number;
  timezone?: string;
  use24Hour: boolean;
  programRetentionHours: number;
}
