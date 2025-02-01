import React, { useState, useCallback, useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
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
}

const ITEMS_PER_PAGE = 50;
const ITEM_HEIGHT = 56;

// Styles for group headers
const headerStyles = {
  container: {
    bgcolor: 'background.default',
    borderBottom: 1,
    borderColor: 'divider',
    py: 1.5,
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

export const ChannelList = forwardRef<{ refresh: () => Promise<void> }, ChannelListProps>(({
  selectedChannel,
  onChannelSelect,
  onToggleFavorite,
  onRefresh,
  onOpenSettings,
}, ref) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  // Load channels with pagination
  const loadChannels = useCallback(async (reset: boolean = false) => {
    try {
      const newPage = reset ? 0 : page;
      const skip = newPage * ITEMS_PER_PAGE;
      
      const response = await channelService.getChannels(skip, ITEMS_PER_PAGE, {
        search: searchTerm
      });

      setChannels(prev => reset ? response.items : [...prev, ...response.items]);
      setHasMore(response.items.length === ITEMS_PER_PAGE);
      setPage(prev => reset ? 1 : prev + 1);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load channels:', error);
      setLoading(false);
    }
  }, [searchTerm, page]);

  // Handle infinite scroll
  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, clientHeight, scrollHeight } = event.currentTarget;
    if (scrollHeight - scrollTop - clientHeight < 50 && !loading && hasMore) {
      loadChannels();
    }
  }, [loading, hasMore, loadChannels]);

  // Handle search with debounce
  const handleSearch = useCallback(debounce((term: string) => {
    setSearchTerm(term);
    setLoading(true);
    setChannels([]);
    setHasMore(true);
    setPage(0);
    if (containerRef.current) {
      containerRef.current.scrollTop = 0;
    }
  }, 300), []);

  // Initial load and search updates
  useEffect(() => {
    loadChannels(true);
  }, [searchTerm]);

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
          const showHeader = !channels[index - 1] || channels[index - 1].group !== channel.group;

          return (
            <React.Fragment key={channel.guide_id}>
              {showHeader && (
                <Box sx={headerStyles.container}>
                  <Typography sx={headerStyles.text}>
                    {channel.group}
                  </Typography>
                </Box>
              )}
              <ListItemButton
                selected={selectedChannel?.guide_id === channel.guide_id}
                onClick={() => {
                  onChannelSelect(channel);
                  navigate(`/channel/${channel.guide_id}`);
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
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
            <CircularProgress />
          </Box>
        )}
        {!loading && channels.length === 0 && (
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
