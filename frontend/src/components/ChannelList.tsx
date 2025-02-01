import React, { useState, useCallback, useEffect, useRef, forwardRef, useImperativeHandle, useMemo } from 'react';
import {
  Box,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Avatar,
  TextField,
  IconButton,
  InputAdornment,
  CircularProgress,
  Typography,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Search as SearchIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Settings as SettingsIcon,
  ChevronRight,
  ChevronLeft,
} from '@mui/icons-material';
import { Channel } from '../models/Channel';
import { channelService } from '../services/channelService';
import { useNavigate } from 'react-router-dom';
import debounce from 'lodash/debounce';
import { format } from 'date-fns';

// Move all helper functions and interfaces to the top
const ITEMS_PER_PAGE = 250;
const ITEM_HEIGHT = 56;
const TIME_BLOCK_WIDTH = 150;
const HEADER_HEIGHT = 48;
const PREFETCH_THRESHOLD = 0.8; // Start loading when user scrolls to 80% of the list

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

// Add type for tab values
type TabValue = 'all' | 'favorites' | 'recent';

// Add interface for program data
interface Program {
  id: string;
  title: string;
  start: Date;
  end: Date;
  duration: number; // in minutes
}

interface ChannelListProps {
  selectedChannel?: Channel;
  onChannelSelect: (channel: Channel) => void;
  onToggleFavorite: (channel: Channel) => void;
  onRefresh?: (refreshFn: (() => Promise<void>) | undefined) => void;
  onOpenSettings?: () => void;
  programs?: Record<string, Program[]>;
  channelListOpen: boolean;
}

// Styles for group headers
const headerStyles = {
  container: {
    display: 'flex',
    bgcolor: 'background.default',
    borderBottom: 1,
    borderColor: 'divider',
    py: 1.5,
    position: 'sticky',
    top: HEADER_HEIGHT,
    zIndex: 1,
  },
  groupSection: {  // New style for the fixed-width group section
    width: 300,
    flexShrink: 0,
    display: 'flex',
    alignItems: 'center',
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
  },
  text: {
    color: 'text.primary',
    fontWeight: 500,
    pl: 3,  // Increased padding to account for the indicator
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    fontSize: '0.8125rem',
  }
};

export const ChannelList = forwardRef<{ refresh: () => Promise<void> }, ChannelListProps>(({
  selectedChannel,
  onChannelSelect,
  onToggleFavorite,
  onRefresh,
  onOpenSettings,
  programs = {},
  channelListOpen,
}, ref) => {
  const [activeTab, setActiveTab] = useState<TabValue>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [prefetching, setPrefetching] = useState(false);  // New state for prefetching
  const [channels, setChannels] = useState<Channel[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const [epgExpanded, setEpgExpanded] = useState(false);
  const timeSlots = useMemo(() => generateTimeSlots(getStartTime()), []);

  // Modify loadChannels to handle tab filters
  const loadChannels = useCallback(async (reset: boolean = false, isPrefetch: boolean = false) => {
    try {
      if (isPrefetch) {
        setPrefetching(true);
      } else {
        setLoading(true);
      }

      const newPage = reset ? 0 : page;
      const skip = newPage * ITEMS_PER_PAGE;
      
      const response = await channelService.getChannels(skip, ITEMS_PER_PAGE, {
        search: searchTerm,
        favoritesOnly: activeTab === 'favorites',
        recentOnly: activeTab === 'recent'
      });

      setChannels(prev => reset ? response.items : [...prev, ...response.items]);
      setHasMore(response.items.length === ITEMS_PER_PAGE);
      setPage(prev => reset ? 1 : prev + 1);
    } catch (error) {
      console.error('Failed to load channels:', error);
    } finally {
      if (isPrefetch) {
        setPrefetching(false);
      } else {
      setLoading(false);
      }
    }
  }, [page, searchTerm, activeTab]);

  // Create a stable debounced scroll handler
  const debouncedScroll = useMemo(
    () => debounce((element: HTMLDivElement) => {
      const { scrollTop, clientHeight, scrollHeight } = element;
      const scrollPercentage = (scrollTop + clientHeight) / scrollHeight;

      // If we're near the bottom and not already loading/prefetching
      if (scrollPercentage > PREFETCH_THRESHOLD && !loading && !prefetching && hasMore) {
        loadChannels(false, true);  // Start prefetching
      }

      // If we've hit the bottom and have prefetched data
      if (scrollHeight - scrollTop - clientHeight < 50 && !loading && hasMore) {
        loadChannels();  // Load the next page normally
      }
    }, 100),
    [loading, prefetching, hasMore, loadChannels]
  );

  // Handle scroll event
  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    if (event.currentTarget) {
      debouncedScroll(event.currentTarget);
    }
  }, [debouncedScroll]);

  // Handle search with debounce
  const handleSearch = useCallback((term: string) => {
    setSearchTerm(term);
    setLoading(true);
    setChannels([]);
    setHasMore(true);
    setPage(0);
    if (containerRef.current) {
      containerRef.current.scrollTop = 0;
    }
  }, []);

  // Add tab change handler
  const handleTabChange = useCallback((_: React.SyntheticEvent, newValue: TabValue) => {
    setActiveTab(newValue);
    setChannels([]);
    setHasMore(true);
    setPage(0);
    if (containerRef.current) {
      containerRef.current.scrollTop = 0;
    }
  }, []);

  // Update useEffect to reload on tab change
  useEffect(() => {
    loadChannels(true);
  }, [searchTerm, activeTab]);

  // Refresh function for parent component
  const refresh = useCallback(async () => {
    setLoading(true);
    setChannels([]);
    setHasMore(true);
    setPage(0);
    await loadChannels(true);
  }, [loadChannels]);

  useImperativeHandle(ref, () => ({
    refresh
  }), [refresh]);

  useEffect(() => {
    if (onRefresh) {
      onRefresh(refresh);
    }
  }, [onRefresh, refresh]);

  // Add helper to calculate program width
  const getProgramWidth = useCallback((duration: number) => {
    return (duration / 30) * TIME_BLOCK_WIDTH;
  }, []);

  // Add helper to calculate program position
  const getProgramPosition = useCallback((start: Date) => {
    const firstSlot = timeSlots[0];
    const diffMinutes = (start.getTime() - firstSlot.getTime()) / (1000 * 60);
    return (diffMinutes / 30) * TIME_BLOCK_WIDTH;
  }, [timeSlots]);

  return (
    <Paper elevation={3} sx={{ 
      height: '100%', 
      display: 'flex', 
      flexDirection: 'column',
      position: 'relative',
      width: 300, // Keep the container at fixed width
    }}>
      {/* Fixed width header section */}
      <Box sx={{ 
        width: 300,
        flexShrink: 0,
        zIndex: 3,
        bgcolor: 'background.paper',
        borderBottom: 1,
        borderColor: 'divider',
      }}>
        {/* Search Bar */}
        <Box sx={{ p: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
          <TextField
            fullWidth
            size="small"
            placeholder="Search channels..."
            onChange={(e) => handleSearch(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
          />
          {onOpenSettings && (
            <IconButton onClick={onOpenSettings} size="small">
              <SettingsIcon />
            </IconButton>
          )}
        </Box>

        {/* Tabs and EPG Toggle */}
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            variant="fullWidth"
            sx={{ borderBottom: 1, borderColor: 'divider', flexGrow: 1 }}
          >
            <Tab label="All" value="all" />
            <Tab label="Favorites" value="favorites" />
            <Tab label="Recent" value="recent" />
          </Tabs>
          <IconButton
            onClick={() => setEpgExpanded(!epgExpanded)}
            sx={{
              borderRadius: '4px 0 0 4px',
              bgcolor: 'background.paper',
              '&:hover': { bgcolor: 'action.hover' },
            }}
          >
            {epgExpanded ? <ChevronLeft /> : <ChevronRight />}
          </IconButton>
        </Box>
      </Box>

      {/* Expandable channels section */}
      <Box
        ref={containerRef}
        onScroll={handleScroll}
        sx={{
          flexGrow: 1,
          overflow: 'auto',
          bgcolor: 'background.default',
          position: 'relative',
          width: channelListOpen && epgExpanded ? `${300 + (timeSlots.length * TIME_BLOCK_WIDTH)}px` : '300px',
          transition: theme => theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
        }}
      >
        {/* Time header - highest z-index */}
        <Box sx={{
          position: 'sticky',
          top: 0,
          zIndex: 2,
          display: 'flex',
          bgcolor: 'background.paper',
          borderBottom: 1,
          borderColor: 'divider',
          height: HEADER_HEIGHT,
        }}>
          {/* Empty space for channel info width */}
          <Box sx={{ width: 300, flexShrink: 0 }} />
          
          {/* Time slots */}
          <Box sx={{ 
            display: channelListOpen && epgExpanded ? 'flex' : 'none',
            height: HEADER_HEIGHT,
          }}>
            {timeSlots.map((time, index) => (
              <Box
                key={time.getTime()}
                sx={{
                  width: TIME_BLOCK_WIDTH,
                  borderLeft: 1,
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
        </Box>

        {/* Channel groups */}
        {channels.map((channel, index) => {
          const showHeader = index === 0 || channels[index - 1].group !== channel.group;

          return (
            <React.Fragment key={`${channel.guide_id}-${index}`}>
              {showHeader && (
                <Box sx={{
                  ...headerStyles.container,
                  width: channelListOpen && epgExpanded ? `${300 + (timeSlots.length * TIME_BLOCK_WIDTH)}px` : '300px',
                  bgcolor: 'background.default',
                  backdropFilter: 'blur(8px)',
                }}>
                  <Box sx={headerStyles.groupSection}>
                    <Typography sx={headerStyles.text}>
                      {channel.group}
                    </Typography>
                  </Box>
                </Box>
              )}
              <Box sx={{ 
                display: 'flex',
                transition: theme => theme.transitions.create('width', {
                  easing: theme.transitions.easing.sharp,
                  duration: theme.transitions.duration.enteringScreen,
                }),
                width: channelListOpen && epgExpanded ? `${300 + (timeSlots.length * TIME_BLOCK_WIDTH)}px` : '300px',
              }}>
                <ListItemButton
                  selected={selectedChannel?.guide_id === channel.guide_id}
                  onClick={async () => {
                    onChannelSelect(channel);
                    navigate(`/channel/${channel.guide_id}`);
                    try {
                      await channelService.updateLastWatched(channel.guide_id);
                    } catch (error) {
                      console.error('Failed to update last watched:', error);
                    }
                  }}
                  sx={{ width: 300, flexShrink: 0 }}
                >
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleFavorite(channel);
                    }}
                    sx={{ mr: 1 }}
                  >
                    {channel.isFavorite ? <StarIcon color="primary" /> : <StarBorderIcon />}
                  </IconButton>
                  <ListItemIcon>
                    <Avatar
                      src={channel.logo}
                      alt={channel.name}
                      variant="square"
                      sx={{ width: 32, height: 32 }}
                    >
                      {channel.name[0]}
                    </Avatar>
                  </ListItemIcon>
                  <ListItemText primary={channel.name} />
                </ListItemButton>

                <Box sx={{ 
                  display: 'flex',
                  overflow: 'hidden',
                  opacity: channelListOpen && epgExpanded ? 1 : 0,
                  transition: 'opacity 0.2s',
                  position: 'relative',
                  height: ITEM_HEIGHT,
                }}>
                  {programs[channel.guide_id]?.map((program) => (
                    <Box
                      key={program.id}
                      sx={{
                        position: 'absolute',
                        left: getProgramPosition(program.start),
                        width: getProgramWidth(program.duration),
                        height: '100%',
                        bgcolor: 'action.hover',
                        borderLeft: 1,
                        borderRight: 1,
                        borderColor: 'divider',
                        display: 'flex',
                        alignItems: 'center',
                        px: 1,
                        overflow: 'hidden',
                        whiteSpace: 'nowrap',
                        textOverflow: 'ellipsis',
                        typography: 'body2',
                        '&:hover': {
                          bgcolor: 'action.selected',
                        },
                      }}
                      title={`${program.title}\n${format(program.start, 'HH:mm')} - ${format(program.end, 'HH:mm')}`}
                    >
                      {program.title}
                    </Box>
                  ))}
                </Box>
              </Box>
            </React.Fragment>
          );
        })}
        {(loading || prefetching) && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
            <CircularProgress />
          </Box>
        )}
        {!loading && !prefetching && channels.length === 0 && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
            <Typography color="text.secondary">
              No channels found
            </Typography>
          </Box>
        )}
      </Box>
    </Paper>
  );
});

export type { ChannelListProps }; 
