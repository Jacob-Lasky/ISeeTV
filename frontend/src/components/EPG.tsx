import React, { useMemo } from 'react';
import { Box, IconButton, Typography, Tabs } from '@mui/material';
import { ChevronRight, ChevronLeft } from '@mui/icons-material';

interface EPGProps {
  open: boolean;
  onToggle: () => void;
  channelListOpen: boolean;
  channels: Channel[];
}

const TIME_BLOCK_WIDTH = 150; // Half the channel list width
const SEARCH_BAR_HEIGHT = 56; // Height of the search bar area
const HEADER_HEIGHT = 48; // Match the height of MUI Tabs

// Helper function to get the most recent half hour
const getStartTime = () => {
  const now = new Date();
  const minutes = now.getMinutes();
  const roundedMinutes = minutes >= 30 ? 30 : 0;
  
  now.setMinutes(roundedMinutes);
  now.setSeconds(0);
  now.setMilliseconds(0);
  
  return now;
};

// Helper function to generate time slots
const generateTimeSlots = (startTime: Date, hours: number = 4) => {
  const slots: Date[] = [];
  const totalSlots = hours * 2; // 2 slots per hour (30 min each)
  
  for (let i = 0; i < totalSlots; i++) {
    const time = new Date(startTime);
    time.setMinutes(time.getMinutes() + (i * 30));
    slots.push(time);
  }
  
  return slots;
};

export const EPG: React.FC<EPGProps> = ({ open, onToggle, channelListOpen, channels }) => {
  const leftPosition = channelListOpen ? 300 : 0;
  const shouldShow = channelListOpen && open;
  const buttonPosition = shouldShow ? leftPosition + 600 : leftPosition;
  
  const timeSlots = useMemo(() => generateTimeSlots(getStartTime()), []);
  
  return (
    <>
      {/* Toggle Button */}
      <IconButton
        onClick={onToggle}
        sx={{
          position: 'fixed',
          left: buttonPosition,
          top: SEARCH_BAR_HEIGHT + 4,
          zIndex: 3,
          bgcolor: 'background.paper',
          borderRadius: '4px 0 0 4px',
          transition: theme => theme.transitions.create('left', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
          visibility: channelListOpen ? 'visible' : 'hidden',
          '&:hover': {
            bgcolor: 'action.hover',
          },
        }}
      >
        {open ? <ChevronLeft /> : <ChevronRight />}
      </IconButton>

      {/* EPG Panel */}
      <Box
        sx={{
          position: 'fixed',
          left: leftPosition,
          top: 0,
          bottom: 0,
          width: shouldShow ? 600 : 0,
          bgcolor: 'background.paper',
          borderLeft: 1,
          borderColor: 'divider',
          transition: theme => theme.transitions.create(['width', 'left'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
          overflow: 'hidden',
          zIndex: 2,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Spacer to match search bar height */}
        <Box sx={{ height: SEARCH_BAR_HEIGHT }} />

        {/* Scrollable container for both header and content */}
        <Box sx={{ 
          flexGrow: 1,
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}>
          {/* Content container with fixed width */}
          <Box sx={{ 
            minWidth: TIME_BLOCK_WIDTH * timeSlots.length,
            height: '100%',
          }}>
            {/* Time Grid Header - Now scrolls with content */}
            <Box sx={{ 
              height: HEADER_HEIGHT,
              borderBottom: 1,
              borderColor: 'divider',
              display: 'flex',
              alignItems: 'center',
              pl: 2,
              bgcolor: 'background.paper',
              position: 'sticky',
              top: 0,
              zIndex: 1,
            }}>
              {timeSlots.map((time, index) => (
                <Box
                  key={time.getTime()}
                  sx={{
                    width: TIME_BLOCK_WIDTH,
                    height: '100%',
                    borderLeft: index > 0 ? 1 : 0,
                    borderColor: 'divider',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    typography: 'body2',
                  }}
                >
                  {time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </Box>
              ))}
            </Box>

            {/* Programs Grid */}
            <Box sx={{ position: 'relative', flexGrow: 1 }}>
              {/* Vertical grid lines */}
              {timeSlots.map((_, index) => (
                <Box
                  key={index}
                  sx={{
                    position: 'absolute',
                    left: `${index * TIME_BLOCK_WIDTH}px`,
                    top: 0,
                    bottom: 0,
                    width: 1,
                    bgcolor: 'divider',
                  }}
                />
              ))}

              {/* Channel rows */}
              {channels.map((channel, index) => (
                <React.Fragment key={channel.guide_id}>
                  {/* Add category header if needed */}
                  {index === 0 || channels[index - 1].group !== channel.group ? (
                    <Box
                      sx={{
                        height: 40,
                        bgcolor: 'background.default',
                        borderBottom: 1,
                        borderColor: 'divider',
                        display: 'flex',
                        alignItems: 'center',
                        px: 2,
                        position: 'relative',
                        '&::before': {
                          content: '""',
                          position: 'absolute',
                          left: 0,
                          top: 0,
                          width: 4,
                          height: '100%',
                          bgcolor: 'primary.main',
                          opacity: 0.7,
                        },
                      }}
                    >
                      <Typography sx={{
                        color: 'text.primary',
                        fontWeight: 500,
                        pl: 1,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                        fontSize: '0.8125rem',
                      }}>
                        {channel.group}
                      </Typography>
                    </Box>
                  ) : null}
                  
                  {/* Channel row */}
                  <Box
                    sx={{
                      height: 56, // Match channel list item height
                      borderBottom: 1,
                      borderColor: 'divider',
                      display: 'flex',
                      alignItems: 'center',
                      px: 2,
                      position: 'relative',
                    }}
                  >
                    {/* Program slots will go here */}
                  </Box>
                </React.Fragment>
              ))}
            </Box>
          </Box>
        </Box>
      </Box>
    </>
  );
}; 