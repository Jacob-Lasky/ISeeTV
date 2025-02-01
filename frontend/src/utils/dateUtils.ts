// Helper function to get the most recent half hour in UTC
export const getStartTime = () => {
  const now = new Date();
  const minutes = now.getUTCMinutes();
  const roundedMinutes = minutes >= 30 ? 30 : 0;
  
  // Create a new date in UTC
  const utcDate = new Date();
  utcDate.setUTCMinutes(roundedMinutes);
  utcDate.setUTCSeconds(0);
  utcDate.setUTCMilliseconds(0);
  
  // Optionally offset by a few hours to show earlier programs
  utcDate.setUTCHours(utcDate.getUTCHours() - 2); // Start 2 hours before current time
  
  return utcDate;
};

// Helper function to generate time slots in UTC
export const generateTimeSlots = (startTime: Date, hours: number = 4) => {
  const slots: Date[] = [];
  const totalSlots = hours * 2; // 2 slots per hour (30 min each)
  
  for (let i = 0; i < totalSlots; i++) {
    const time = new Date(startTime);
    time.setUTCMinutes(time.getUTCMinutes() + (i * 30));
    slots.push(time);
  }
  
  return slots;
}; 