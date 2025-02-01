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
} from '@mui/icons-material';
import { Channel } from '../models/Channel';
import { channelService } from '../services/channelService';
import { useNavigate } from 'react-router-dom';
import debounce from 'lodash/debounce';

interface ChannelListProps {
  selectedChannel?: Channel;
  onChannelSelect: (channel: Channel) => void;
  onToggleFavorite: (channel: Channel) => void;
  onRefresh?: (refreshFn: (() => Promise<void>) | undefined) => void;
  onOpenSettings?: () => void;
  onChannelsChange: (channels: Channel[]) => void;
}

const ITEMS_PER_PAGE = 250
const ITEM_HEIGHT = 56;
const PREFETCH_THRESHOLD = 0.8; // Start loading when user scrolls to 80% of the list

// Styles for group headers
const headerStyles = {
  container: {
    bgcolor: 'background.default',
    borderBottom: 1,
    borderColor: 'divider',
    py: 1.5,
    px: 2,
    position: 'sticky',
    top: 0,
    zIndex: 1,
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
    pl: 1,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    fontSize: '0.8125rem',
  }
};

// Add type for tab values
type TabValue = 'all' | 'favorites' | 'recent';

export const ChannelList = forwardRef<{ refresh: () => Promise<void> }, ChannelListProps>(({
  selectedChannel,
  onChannelSelect,
  onToggleFavorite,
  onRefresh,
  onOpenSettings,
  onChannelsChange,
}, ref) => {
  // Add activeTab state
  const [activeTab, setActiveTab] = useState<TabValue>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [prefetching, setPrefetching] = useState(false);  // New state for prefetching
  const [channels, setChannels] = useState<Channel[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

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

  useEffect(() => {
    if (onChannelsChange) {
      onChannelsChange(channels);
    }
  }, [channels, onChannelsChange]);

  return (
    <Paper elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
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

      {/* Add Tabs */}
      <Tabs
        value={activeTab}
        onChange={handleTabChange}
        variant="fullWidth"
        sx={{ borderBottom: 1, borderColor: 'divider' }}
      >
        <Tab label="All" value="all" />
        <Tab label="Favorites" value="favorites" />
        <Tab label="Recent" value="recent" />
      </Tabs>

      {/* Channel List */}
      <Box
        ref={containerRef}
        onScroll={handleScroll}
        sx={{
          flexGrow: 1,
          overflow: 'auto',
          bgcolor: 'background.default'
        }}
      >
        {channels.map((channel, index) => {
          const showHeader = index === 0 || channels[index - 1].group !== channel.group;

          return (
            <React.Fragment key={`${channel.guide_id}-${index}`}>
              {showHeader && (
                <Box sx={headerStyles.container}>
                  <Typography sx={headerStyles.text}>
                    {channel.group}
                  </Typography>
                </Box>
              )}
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
                sx={{ 
                  height: ITEM_HEIGHT,
                  '&:hover': {
                    bgcolor: 'action.hover',
                  },
                  transition: 'background-color 0.2s'
                }}
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
