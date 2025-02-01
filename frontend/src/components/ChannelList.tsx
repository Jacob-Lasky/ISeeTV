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
import { format } from 'date-fns';
import { Epg, Layout, useEpg, useProgram, ProgramBox, ProgramContent, ProgramFlex, ProgramStack, ProgramTitle, ProgramText, ChannelBox, ChannelLogo } from 'planby';
import { useTheme } from '@mui/material/styles';

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

// Update interfaces to match Planby's expected format
interface PlanbyProgram {
  id: string;
  title: string;
  since: string;  // ISO string
  till: string;   // ISO string
  channelUuid: string;
  image?: string;
}

interface PlanbyChannel {
  uuid: string;
  logo?: string;
  name: string;
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
  const theme = useTheme();

  // Move planbyTheme inside the component to access theme
  const planbyTheme = useMemo(() => ({
    primary: {
      600: theme.palette.mode === 'dark' ? '#171923' : '#f5f5f5',
      900: theme.palette.mode === 'dark' ? '#1f1f1f' : '#ffffff',
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
    gradient: {
      blue: {
        300: theme.palette.primary.light,
        600: theme.palette.primary.main,
        900: theme.palette.primary.dark,
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

  // Convert channels and programs to Planby format
  const planbyChannels = useMemo<PlanbyChannel[]>(() => 
    channels.map(channel => ({
      uuid: channel.guide_id,
      name: channel.name,
      logo: channel.logo,
    })), [channels]
  );

  const planbyPrograms = useMemo<PlanbyProgram[]>(() => {
    const allPrograms: PlanbyProgram[] = [];
    Object.entries(programs).forEach(([channelId, channelPrograms]) => {
      channelPrograms.forEach(program => {
        allPrograms.push({
          id: program.id,
          title: program.title,
          since: program.start.toISOString(),
          till: program.end.toISOString(),
          channelUuid: channelId,
        });
      });
    });
    return allPrograms;
  }, [programs]);

  // Initialize Planby EPG
  const { getEpgProps, getLayoutProps } = useEpg({
    channels: planbyChannels,
    epg: planbyPrograms,
    startDate: getStartTime().toISOString(),
    width: channelListOpen ? epgExpanded ? 1200 : 300 : 0,
    height: containerRef.current?.clientHeight || 800,
    itemHeight: 70,
    sidebarWidth: 300,
    theme: planbyTheme,
  });

  // Custom Program component using Material-UI
  const ProgramItem = ({ program, ...rest }: any) => {
    const { styles, formatTime, isLive } = useProgram({ program, ...rest });

    const { data } = program;
    const { title, since, till } = data;

    const sinceTime = formatTime(since);
    const tillTime = formatTime(till);

    return (
      <ProgramBox width={styles.width} style={styles.position}>
        <Card 
          sx={{ 
            height: '100%',
            bgcolor: isLive ? 'action.selected' : 'background.paper',
            borderRadius: 0,
            '&:hover': {
              bgcolor: 'action.hover',
            }
          }}
        >
          <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
            <Stack spacing={0.5}>
              <Typography variant="subtitle2" noWrap>
                {title}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {sinceTime} - {tillTime}
              </Typography>
            </Stack>
          </CardContent>
        </Card>
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
            alignItems: 'center',
            gap: 1,
          }}>
            <Avatar
              src={logo}
              alt={name}
              variant="square"
              sx={{ width: 32, height: 32 }}
            />
            <Typography noWrap>
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

      {/* Update EPG section */}
      <Box 
        ref={containerRef} 
        sx={{ 
          flexGrow: 1, 
          overflow: 'hidden',
          bgcolor: 'background.default',
        }}
      >
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
      {(loading || prefetching) && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
          <CircularProgress />
        </Box>
      )}
    </Paper>
  );
});

export type { ChannelListProps }; 
