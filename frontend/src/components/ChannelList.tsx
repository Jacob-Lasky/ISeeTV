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
  Card,
  CardContent,
  Stack,
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
import { format, addHours } from 'date-fns';
import { zonedTimeToUtc, utcToZonedTime } from 'date-fns-tz';
import { Epg, Layout, useEpg, useProgram, ProgramBox, ProgramContent, ProgramFlex, ProgramStack, ProgramTitle, ProgramText, ChannelBox, ChannelLogo, ProgramImage } from 'planby';
import { useTheme } from '@mui/material/styles';
import { generateTimeSlots, formatTimeWithTimezone, localToUtc, getTodayOffsetDate } from '../utils/dateUtils';
import { Settings } from '../models/Settings';

const TIME_BLOCK_WIDTH = 150;
const HEADER_HEIGHT = 48;
const HOUR_WIDTH = TIME_BLOCK_WIDTH * 2;
const SCROLLBAR_WIDTH = 20; // Standard scrollbar width

// Add type for tab values
type TabValue = 'all' | 'favorites' | 'recent';

// Add interface for program data
interface Program {
  id: string;
  title: string;
  start: Date;
  end: Date;
  duration: number;
  description: string;
  category: string;
}

// match Planby's expected format
interface PlanbyProgram {
  id: string;
  title: string;
  channelUuid: string;
  image: string;
  since: string;    // ISO string
  till: string;     // ISO string
  description: string;
  category: string;
  isLive?: boolean;
  position?: {      // optional position data
    top: number;
    height: number;
    width: number;
    left: number;
  };
}

interface PlanbyChannel {
  uuid: string;  // unique identifier
  logo: string;  // required by Planby
  name: string;
  position?: {   // optional position data
    top: number;
    height: number;
  };
}

interface ChannelListProps {
  selectedChannel?: Channel;
  onChannelSelect: (channel: Channel) => void;
  onToggleFavorite: (channel: Channel) => void;
  onRefresh?: (refreshFn: (() => Promise<void>) | undefined) => void;
  onOpenSettings?: () => void;
  onChannelsChange?: (channels: Channel[]) => void;
  programs?: Record<string, Program[]>;
  channelListOpen: boolean;
  timezone?: string;
  settings?: Settings;
  isMobile?: boolean;
}

export const ChannelList = forwardRef<{ refresh: () => Promise<void> }, ChannelListProps>(({
  selectedChannel,
  onChannelSelect,
  onToggleFavorite,
  onRefresh,
  onOpenSettings,
  onChannelsChange,
  programs = {},
  channelListOpen,
  timezone = Intl.DateTimeFormat().resolvedOptions().timeZone,
  settings,
  isMobile,
}, ref) => {
  // Update headerStyles
  const headerStyles = {
    container: {
      width: isMobile ? '100%' : 300,
      flexShrink: 0,
      zIndex: 3,
      bgcolor: 'background.paper',
      borderBottom: 1,
      borderColor: 'divider',
      display: 'flex',
      flexDirection: 'column',
    },
    groupSection: {  
      width: isMobile ? '100%' : 300,
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
      pl: 3,
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
      fontSize: '0.8125rem',
    }
  };

  const [activeTab, setActiveTab] = useState<TabValue>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const [epgExpanded, setEpgExpanded] = useState(false);
  const timeSlots = useMemo(() => generateTimeSlots(getTodayOffsetDate(settings?.guideStartHour ?? -1, timezone)), []);
  const theme = useTheme();

  // Move planbyTheme inside the component to access theme
  const planbyTheme = useMemo(() => ({
    primary: {
      600: theme.palette.mode === 'dark' ? '#040d1e' : '#b2eff7', // finished and upcoming programs
      900: theme.palette.mode === 'dark' ? '#1f1f1f' : '#ffffff', // guide background
    },
    grey: { 
      300: theme.palette.mode === 'dark' ? '#d1d1d1' : '#757575' 
    },
    white: theme.palette.mode === 'dark' ? '#fff' : '#000',
    green: {
      300: theme.palette.primary.main, // Use MUI primary color
    },
    loader: {
      teal: theme.palette.primary.light,
      purple: theme.palette.primary.main,
      pink: theme.palette.primary.dark,
      bg: theme.palette.mode === 'dark' ? '#171923db' : '#f5f5f5db',
    },
    scrollbar: {
      border: theme.palette.divider,
      thumb: {
        bg: theme.palette.mode === 'dark' ? '#e1e1e1' : '#757575',
      },
    },
    // live channel gradient
    gradient: {
      blue: {
        300: theme.palette.mode === 'dark' ? '#040d1e': '#b2eff7',
        600: theme.palette.mode === 'dark' ? '#001d31': '#ceecf0',
        900: theme.palette.mode === 'dark' ? '#040d1e': '#b2eff7',
      },
    },
    text: {
      grey: {
        300: theme.palette.text.primary,
        500: theme.palette.text.secondary,
      },
    },
    timeline: {
      divider: {
        bg: theme.palette.divider,
      },
    },
  }), [theme]);

  // Modify loadChannels to always load channels
  const loadChannels = useCallback(async (reset: boolean = false) => {
    try {
      setLoading(true);
      const response = await channelService.getChannels(0, {
        search: searchTerm,
        favoritesOnly: activeTab === 'favorites',
        recentOnly: activeTab === 'recent'
      });

      setChannels(response.items);
      setHasMore(false);
      setPage(1);
    } catch (error) {
      console.error('Failed to load channels:', error);
    } finally {
      setLoading(false);
    }
  }, [searchTerm, activeTab]);

  // Update the effect to load channels on mount and when dependencies change
  useEffect(() => {
    loadChannels(true);
  }, [searchTerm, activeTab, loadChannels]);

  // Simplify scroll handler since we don't need pagination anymore
  const debouncedScroll = useMemo(
    () => debounce((element: HTMLDivElement) => {
      // Keep scroll tracking for future use if needed
      const { scrollTop, clientHeight, scrollHeight } = element;
      const scrollPercentage = (scrollTop + clientHeight) / scrollHeight;
    }, 100),
    []
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

  // Keep the refresh function for parent component
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

  // Convert channels to Planby format
  const planbyChannels = useMemo<PlanbyChannel[]>(() => 
    channels.map((channel, index) => ({
      uuid: channel.channel_id,
      name: channel.name,
      logo: channel.logo || 'https://via.placeholder.com/150',  // Provide default logo
      position: {
        top: index * 70,  // matches itemHeight in useEpg config
        height: 70
      }
    })), [channels]
  );

  // Convert programs to Planby format
  const planbyPrograms = useMemo<PlanbyProgram[]>(() => {
    const allPrograms: PlanbyProgram[] = [];
    const now = new Date();
    const startTime = getTodayOffsetDate(settings?.guideStartHour ?? -1, timezone);

    Object.entries(programs).forEach(([channelId, channelPrograms]) => {
      const channelIndex = channels.findIndex(c => c.channel_id === channelId);
      if (channelIndex === -1) return;

      channelPrograms.forEach(program => {
        const startDate = utcToZonedTime(new Date(program.start), timezone);
        const endDate = utcToZonedTime(new Date(program.end), timezone);
        
        // Calculate position data
        const durationMs = endDate.getTime() - startDate.getTime();
        const durationMinutes = durationMs / (1000 * 60);
        const width = (durationMinutes / 30) * TIME_BLOCK_WIDTH;
        const left = ((startDate.getTime() - startTime.getTime()) / (1000 * 60 * 30)) * TIME_BLOCK_WIDTH;

        allPrograms.push({
          id: program.id,
          title: program.title,
          since: startDate.toISOString(),
          till: endDate.toISOString(),
          channelUuid: channelId,
          image: 'https://via.placeholder.com/150',
          description: program.description || 'No description available',
          category: program.category || 'Uncategorized',
          isLive: startDate <= now && endDate >= now,
          position: {
            top: channelIndex * 70,
            height: 70,
            width,
            left
          }
        });
      });
    });
    return allPrograms;
  }, [programs, channels, timezone]);

  // Update where we create the dates
  // for example 1738620000 is 2025-02-04 10:00:00 but in UTC, while I'm at EST
  const guideStartHour = settings?.guideStartHour ?? -1; // Default 2 hours back
  const guideEndHour = settings?.guideEndHour ?? 12;    // Default 12 hours forward
  const guideStartDate = getTodayOffsetDate(guideStartHour, timezone);
  const guideEndDate = getTodayOffsetDate(guideEndHour, timezone);
  const formattedStartDate = format(guideStartDate, 'yyyy-MM-dd\'T\'HH:mm:ss');
  const formattedEndDate = format(guideEndDate, 'yyyy-MM-dd\'T\'HH:mm:ss');

  // Add height state
  const [containerHeight, setContainerHeight] = useState(window.innerHeight - HEADER_HEIGHT);

  // Update the height observer effect
  useEffect(() => {
    const updateHeight = () => {
      if (containerRef.current) {
        const viewportHeight = window.innerHeight;
        const containerTop = containerRef.current.getBoundingClientRect().top;
        const newHeight = viewportHeight - containerTop;
        setContainerHeight(newHeight);
      }
    };

    // Initial height calculation
    updateHeight();

    // Update height on resize
    window.addEventListener('resize', updateHeight);
    
    // Create resize observer for parent element changes
    const resizeObserver = new ResizeObserver(updateHeight);
    if (containerRef.current?.parentElement) {
      resizeObserver.observe(containerRef.current.parentElement);
    }

    return () => {
      window.removeEventListener('resize', updateHeight);
      resizeObserver.disconnect();
    };
  }, []);

  // Add a constant for expanded width percentage
  const EXPANDED_WIDTH_PERCENTAGE = 80; // 80% of viewport width

  // First, declare the width state
  const [epgWidth, setEpgWidth] = useState(() => 
    channelListOpen 
      ? epgExpanded 
        ? isMobile
          ? window.innerWidth  // Full width on mobile
          : Math.min(window.innerWidth * (EXPANDED_WIDTH_PERCENTAGE/100), 1200)
        : 300 
      : 0
  );

  // Then use it in the EPG configuration
  const { getEpgProps, getLayoutProps } = useEpg({
    channels: planbyChannels,
    epg: planbyPrograms,
    width: epgWidth,
    height: containerHeight,
    itemHeight: 70,
    // Adjust sidebar width when expanded on mobile
    sidebarWidth: isMobile && epgExpanded 
      ? window.innerWidth * 0.25  // 1/4 of screen width when expanded
      : isMobile 
        ? window.innerWidth 
        : 300,
    theme: planbyTheme,
    isBaseTimeFormat: true,
    isSidebar: true,
    isTimeline: true,
    dayWidth: 24 * HOUR_WIDTH,
    isLine: epgExpanded,
    startDate: formattedStartDate,
    endDate: formattedEndDate,
  });

  // Keep the resize effects after
  useEffect(() => {
    const updateWidth = () => {
      setEpgWidth(
        channelListOpen 
          ? epgExpanded 
            ? isMobile
              ? window.innerWidth  // Full width on mobile
              : Math.min(window.innerWidth * (EXPANDED_WIDTH_PERCENTAGE/100), 1200)
            : 300 + SCROLLBAR_WIDTH
          : 0
      );
    };

    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, [channelListOpen, epgExpanded, isMobile]);

  useEffect(() => {
    setEpgWidth(
      channelListOpen 
        ? epgExpanded 
          ? isMobile
            ? window.innerWidth  // Full width on mobile
            : Math.min(window.innerWidth * (EXPANDED_WIDTH_PERCENTAGE/100), 1200)
          : 300 + SCROLLBAR_WIDTH
        : 0
    );
  }, [channelListOpen, epgExpanded, isMobile]);

  // Custom Program component using Material-UI
  const ProgramItem = ({ program, ...rest }: any) => {
    const { styles, formatTime, isLive, isMinWidth } = useProgram({ program, ...rest });

    const { data } = program;
    const { image, title, since, till, description, category } = data;

    const sinceTime = formatTimeWithTimezone(new Date(since), timezone);
    const tillTime = formatTimeWithTimezone(new Date(till), timezone);

    return (
      <ProgramBox width={styles.width} style={styles.position}>
        <ProgramContent width={styles.width} isLive={isLive}>
          <ProgramFlex>
            {isLive && isMinWidth && <ProgramImage src={image} alt="Preview" />}
            <ProgramStack>
              <ProgramTitle>{title}</ProgramTitle>
              <ProgramText>
                {sinceTime} - {tillTime}
              </ProgramText>
              {category && (
                <ProgramText>
                  {category}
                </ProgramText>
              )}
              {description && isMinWidth && (
                <ProgramText>
                  {description}
                </ProgramText>
              )}
            </ProgramStack>
          </ProgramFlex>
        </ProgramContent>
      </ProgramBox>
    );
  };

  // Custom Channel component using Material-UI
  const ChannelItem = ({ channel }: { channel: any }) => {
    const { position, logo, name } = channel;
    return (
      <ChannelBox {...position}>
        <Card sx={{ 
          height: '100%', 
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          borderRadius: 0,
          bgcolor: 'background.paper',
        }}>
          <CardContent sx={{ 
            p: 1, 
            '&:last-child': { pb: 1 },
            display: 'flex',
            alignItems: 'flex-start',
            gap: 1,
            width: '100%',
          }}>
            <Avatar
              src={logo}
              alt={name}
              variant="square"
              sx={{ 
                width: 32, 
                height: 32,
                flexShrink: 0
              }}
            />
            <Typography 
              sx={{ 
                wordBreak: 'break-word',
                whiteSpace: 'normal',
                overflow: 'hidden',
                fontSize: '0.875rem',
                lineHeight: 1.2,
                maxHeight: '2.4em',
                WebkitLineClamp: 2,
                display: '-webkit-box',
                WebkitBoxOrient: 'vertical',
              }}
            >
              {name}
            </Typography>
          </CardContent>
        </Card>
      </ChannelBox>
    );
  };

  return (
    <Paper elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Fixed width header section */}
      <Box sx={headerStyles.container}>
        {/* Search Bar */}
        <Box sx={{ 
          p: 1, 
          display: 'flex', 
          alignItems: 'center', 
          gap: 1,
          // Add margin-right when mobile and channel list is open
          mr: isMobile && channelListOpen ? 5 : 0  // Add space for collapse button
        }}>
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
            sx={{ flexGrow: 1 }}
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

      {/* Update EPG section */}
      <Box 
        ref={containerRef} 
        sx={{ 
          flexGrow: 1, 
          overflow: 'hidden',
          bgcolor: 'background.default',
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          height: containerHeight,
        }}
      >
        {/* Add overlay text */}
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            height: 60,
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            px: 2,
            color: 'text.primary',
            pointerEvents: 'none',
            // Hide when guide is expanded on mobile
            opacity: isMobile && epgExpanded ? 0 : 1,
            visibility: isMobile && epgExpanded ? 'hidden' : 'visible',
          }}
        >
          <Stack>
            <Typography>{channels.length} Channels</Typography>
            <Typography>{planbyPrograms.length} Programs</Typography>
          </Stack>
        </Box>
        <Epg {...getEpgProps()}>
          <Layout
            {...getLayoutProps()}
            renderProgram={({ program, ...rest }) => (
              <ProgramItem key={program.data.id} program={program} {...rest} />
            )}
            renderChannel={({ channel }) => (
              <ChannelItem key={channel.uuid} channel={channel} />
            )}
          />
        </Epg>
      </Box>

      {/* Keep loading states */}
      {(loading) && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
          <CircularProgress />
        </Box>
      )}
    </Paper>
  );
});

export type { ChannelListProps }; 
