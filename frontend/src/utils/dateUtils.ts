import { format, addHours } from 'date-fns';
import { fromZonedTime, toZonedTime } from 'date-fns-tz';

// Get user's timezone from browser, or read from settings
export const getUserTimezone = (): string => {
  const timezone = localStorage.getItem('timezone');
  if (timezone) {
    return timezone;
  }
  else {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  }
};

// Convert local time to UTC
export const localToUtc = (date: Date, timezone: string = getUserTimezone()): Date => {
  return fromZonedTime(date, timezone);
};

// Convert UTC to local time
export const utcToLocal = (date: Date, timezone: string = getUserTimezone()): Date => {
  return toZonedTime(date, timezone);
};

// Format time with timezone
export const formatTimeWithTimezone = (date: Date, timezone: string = getUserTimezone()): string => {
  const localDate = toZonedTime(date, timezone);
  return format(localDate, 'HH:mm');
};

// Generate time slots for the EPG
export const generateTimeSlots = (startTime: Date, timezone: string = getUserTimezone()): Date[] => {
  const slots: Date[] = [];
  const localStart = toZonedTime(startTime, timezone);
  
  for (let i = 0; i < 48; i++) {
    slots.push(addHours(localStart, i * 0.5));
  }
  
  return slots;
}; 

export const getTodayOffsetDate = (offsetHours: number = 0, zero_minute_second: boolean = true): Date => {
  const today = new Date();
  const offsetDate = addHours(today, offsetHours);
  if (zero_minute_second) {
    offsetDate.setMinutes(0);
    offsetDate.setSeconds(0);
  }
  return offsetDate;
};
