// Helper function to get the most recent half hour with UTC offset
export const getStartTime = (utcOffset: number = 0) => {
  const now = new Date();
  
  // Apply UTC offset
  const offsetMs = utcOffset * 60 * 60 * 1000; // Convert hours to milliseconds
  const localTime = new Date(now.getTime() + offsetMs);
  
  // Round to nearest 30 minutes
  const minutes = localTime.getUTCMinutes();
  const roundedMinutes = minutes >= 30 ? 30 : 0;
  
  // Create new date with rounded minutes
  const roundedTime = new Date(localTime);
  roundedTime.setUTCMinutes(roundedMinutes);
  roundedTime.setUTCSeconds(0);
  roundedTime.setUTCMilliseconds(0);
  
  // Start 1 hour before current time
  roundedTime.setUTCHours(roundedTime.getUTCHours() - 1);
  
  return roundedTime;
};

// Helper function to generate time slots with UTC offset
export const generateTimeSlots = (startTime: Date, hours: number = 13) => {
  const slots: Date[] = [];
  const totalSlots = hours * 2; // 2 slots per hour (30 min each)
  
  for (let i = 0; i < totalSlots; i++) {
    const time = new Date(startTime);
    time.setUTCMinutes(time.getUTCMinutes() + (i * 30));
    slots.push(time);
  }
  
  return slots;
};

// Helper to format time with UTC offset
export const formatTimeWithOffset = (date: Date, utcOffset: number = 0): string => {
  const offsetMs = utcOffset * 60 * 60 * 1000;
  const localTime = new Date(date.getTime() + offsetMs);
  return localTime.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: true 
  });
}; 