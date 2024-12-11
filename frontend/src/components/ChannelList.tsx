import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Box,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Avatar,
  TextField,
  IconButton,
  Tabs,
  Tab,
  InputAdornment,
  CircularProgress,
} from '@mui/material';
import {
  Search as SearchIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  ExpandLess,
  ExpandMore,
} from '@mui/icons-material';
import { Channel } from '../models/Channel';
import { channelService } from '../services/channelService';
import { ChannelGroup } from '../types/api';
import { recentChannelsService } from '../services/recentChannelsService';
import { FixedSizeList } from 'react-window';
import AutoSizer from 'react-virtualized-auto-sizer';

export {};

interface ChannelListProps {
  selectedChannel?: Channel;
  onChannelSelect: (channel: Channel) => void;
  onToggleFavorite: (channel: Channel) => void;
  onRefresh?: (refreshFn: (() => Promise<void>) | undefined) => void;
  showChannelNumbers?: boolean;
  onToggleChannelNumbers?: () => void;
}

type TabValue = 'all' | 'favorites' | 'recent';

interface ChannelListItemProps {
  channel: Channel;
  selected: boolean;
  onSelect: (channel: Channel) => void;
  onToggleFavorite: (channel: Channel) => void;
  indented?: boolean;
  showChannelNumbers?: boolean;
  style?: React.CSSProperties;
}

const ChannelListItem: React.FC<ChannelListItemProps> = ({
  channel,
  selected,
  onSelect,
  onToggleFavorite,
  indented = false,
  showChannelNumbers = false,
  style,
}) => (
  <ListItemButton
    selected={selected}
    onClick={() => onSelect(channel)}
    sx={{ pl: indented ? 4 : 2 }}
    style={style}
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
    <ListItemText
      primary={channel.name}
      secondary={showChannelNumbers ? channel.channel_number : undefined}
    />
  </ListItemButton>
);

interface TabState {
  scrollPosition: number;
  expandedGroups: Record<string, boolean>;
}

interface VirtualizedChannelListProps {
  items: (Channel | ChannelGroup)[];
  expandedGroups: Record<string, boolean>;
  onToggleGroup: (group: string) => void;
  selectedChannel?: Channel;
  onChannelSelect: (channel: Channel) => void;
  onToggleFavorite: (channel: Channel) => void;
  showChannelNumbers?: boolean;
  initialScrollOffset?: number;
  onScroll?: (scrollOffset: number) => void;
}

interface AutoSizerProps {
  height: number;
  width: number;
}

const VirtualizedChannelList: React.FC<VirtualizedChannelListProps> = ({
  items,
  expandedGroups,
  onToggleGroup,
  selectedChannel,
  onChannelSelect,
  onToggleFavorite,
  showChannelNumbers,
  initialScrollOffset = 0,
  onScroll,
}) => {
  const listRef = useRef<FixedSizeList>(null);

  // Restore scroll position when items change
  useEffect(() => {
    if (listRef.current && initialScrollOffset > 0) {
      listRef.current.scrollTo(initialScrollOffset);
    }
  }, [initialScrollOffset, items]);

  const handleScroll = ({ scrollOffset }: { scrollOffset: number }) => {
    onScroll?.(scrollOffset);
  };

  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const item = items[index];
    
    if (!item) return null;

    if ('count' in item) { // Group header
      return (
        <ListItemButton 
          onClick={() => onToggleGroup(item.name)}
          style={style}
        >
          <ListItemText primary={`${item.name} (${item.count})`} />
          {expandedGroups[item.name] ? <ExpandLess /> : <ExpandMore />}
        </ListItemButton>
      );
    }
    
    // Channel item
    return (
      <ChannelListItem
        channel={item}
        selected={item.channel_number === selectedChannel?.channel_number}
        onSelect={onChannelSelect}
        onToggleFavorite={onToggleFavorite}
        showChannelNumbers={showChannelNumbers}
        style={style}
      />
    );
  };

  return (
    <AutoSizer>
      {({ height, width }: AutoSizerProps) => (
        <FixedSizeList
          ref={listRef}
          height={height}
          width={width}
          itemCount={items.length}
          itemSize={56}
          initialScrollOffset={initialScrollOffset}
          onScroll={handleScroll}
        >
          {Row}
        </FixedSizeList>
      )}
    </AutoSizer>
  );
};

export const ChannelList: React.FC<ChannelListProps> = ({
  selectedChannel,
  onChannelSelect,
  onToggleFavorite,
  onRefresh,
  showChannelNumbers = false,
  onToggleChannelNumbers,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState<TabValue>('all');
  const [channelInput, setChannelInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
  const [groups, setGroups] = useState<ChannelGroup[]>([]);
  const [groupChannels, setGroupChannels] = useState<Record<string, Channel[]>>({});
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');
  const searchTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);

  const filteredChannels = React.useMemo(() => {
    let filtered = channels;

    if (activeTab === 'favorites') {
      filtered = filtered.filter(c => c.isFavorite);
    } else if (activeTab === 'recent') {
      filtered = recentChannelsService.getRecentChannels();
    }

    if (debouncedSearchTerm) {
      const search = debouncedSearchTerm.toLowerCase();
      filtered = filtered.filter(c => 
        c.name.toLowerCase().includes(search) ||
        c.channel_number.toString().includes(search)
      );
    }

    return filtered;
  }, [channels, debouncedSearchTerm, activeTab]);

  const virtualizedItems = React.useMemo(() => {
    if (activeTab === 'all' && !debouncedSearchTerm) {
      return groups.reduce<(Channel | ChannelGroup)[]>((acc, group) => {
        acc.push(group);
        if (expandedGroups[group.name] && groupChannels[group.name]) {
          acc.push(...groupChannels[group.name]);
        }
        return acc;
      }, []);
    }
    
    return filteredChannels;
  }, [
    activeTab,
    debouncedSearchTerm,
    groups,
    expandedGroups,
    groupChannels,
    filteredChannels
  ]);

  const [tabStates, setTabStates] = useState<Record<TabValue, TabState>>({
    all: {
      scrollPosition: parseInt(localStorage.getItem('channelListScroll_all') || '0'),
      expandedGroups: JSON.parse(localStorage.getItem('channelListGroups_all') || '{}'),
    },
    favorites: {
      scrollPosition: parseInt(localStorage.getItem('channelListScroll_favorites') || '0'),
      expandedGroups: JSON.parse(localStorage.getItem('channelListGroups_favorites') || '{}'),
    },
    recent: {
      scrollPosition: parseInt(localStorage.getItem('channelListScroll_recent') || '0'),
      expandedGroups: JSON.parse(localStorage.getItem('channelListGroups_recent') || '{}'),
    },
  });

  const initiateSearch = useCallback((term: string) => {
    setDebouncedSearchTerm(term);
  }, []);

  const loadChannels = useCallback(async (loadMore = false) => {
    try {
      setLoading(true);
      const response = await channelService.getChannels(
        0,  // Start from beginning
        1000,  // Load more items at once
        {
          search: debouncedSearchTerm,
          group: activeTab === 'all' ? undefined : activeTab,
          favoritesOnly: activeTab === 'favorites'
        }
      );

      setChannels(response.items);
    } catch (error) {
      console.error('Failed to load channels:', error);
    } finally {
      setLoading(false);
    }
  }, [debouncedSearchTerm, activeTab]);

  const loadGroups = useCallback(async () => {
    try {
      const groups = await channelService.getGroups();
      setGroups(groups);
      
      // Initialize expanded state for all groups
      const savedExpandedGroups = JSON.parse(
        localStorage.getItem(`channelListGroups_${activeTab}`) || '{}'
      );
      
      setExpandedGroups(prev => {
        const newState = { ...prev };
        groups.forEach((group: ChannelGroup) => {
          // Use saved state if available, otherwise default to collapsed
          newState[group.name] = savedExpandedGroups[group.name] || false;
        });
        return newState;
      });

      // Load channels for any groups that should be expanded
      const expandedGroupNames = Object.entries(savedExpandedGroups)
        .filter(([_, isExpanded]) => isExpanded)
        .map(([groupName]) => groupName);

      if (expandedGroupNames.length > 0) {
        setLoading(true);
        try {
          const promises = expandedGroupNames.map(group =>
            channelService.getChannels(0, 1000, { group })
          );

          const responses = await Promise.all(promises);
          const newGroupChannels: Record<string, Channel[]> = {};
          
          expandedGroupNames.forEach((groupName, index) => {
            newGroupChannels[groupName] = responses[index].items;
          });

          setGroupChannels(prev => ({
            ...prev,
            ...newGroupChannels
          }));
        } catch (error) {
          console.error('Failed to load channels for expanded groups:', error);
        } finally {
          setLoading(false);
        }
      }
    } catch (error) {
      console.error('Failed to load groups:', error);
    }
  }, [activeTab]);

  // Add an initialization effect
  useEffect(() => {
    const initializeList = async () => {
      await loadGroups();
      
      // If we're not on the "all" tab, load appropriate channels
      if (activeTab === 'favorites') {
        loadChannels(false);
      } else if (activeTab === 'recent') {
        const recentChannels = recentChannelsService.getRecentChannels();
        setChannels(recentChannels);
      }
    };

    initializeList();
  }, [activeTab, loadChannels, loadGroups]);

  const handleChannelInput = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      const channel = channels.find(c => c.channel_number === parseInt(channelInput));
      if (channel) {
        onChannelSelect(channel);
        setChannelInput('');
      }
    }
  };

  const handleToggleFavorite = async (channel: Channel) => {
    try {
      // Optimistically update the UI
      const newFavoriteStatus = !channel.isFavorite;
      
      // Update all channel states at once
      const updateChannelInState = (ch: Channel) => 
        ch.channel_number === channel.channel_number 
          ? { ...ch, isFavorite: newFavoriteStatus }
          : ch;

      setChannels(prev => prev.map(updateChannelInState));
      setGroupChannels(prev => {
        const newState = { ...prev };
        Object.keys(newState).forEach(group => {
          if (newState[group]) {
            newState[group] = newState[group].map(updateChannelInState);
          }
        });
        return newState;
      });

      // Call the backend to toggle the favorite status
      const updatedChannel = await channelService.toggleFavorite(channel.channel_number);

      // Ensure the UI reflects the backend's response
      setChannels(prev => prev.map(ch => 
        ch.channel_number === updatedChannel.channel_number 
          ? { ...ch, isFavorite: updatedChannel.isFavorite }
          : ch
      ));

      // If we're in favorites tab and unfavoriting, remove the channel
      if (activeTab === 'favorites' && !updatedChannel.isFavorite) {
        setChannels(prev => prev.filter(ch => ch.channel_number !== updatedChannel.channel_number));
      }
      // If we're in favorites tab and favoriting, add the channel
      else if (activeTab === 'favorites' && updatedChannel.isFavorite) {
        setChannels(prev => {
          if (!prev.some(ch => ch.channel_number === updatedChannel.channel_number)) {
            return [...prev, updatedChannel];
          }
          return prev;
        });
      }

    } catch (error) {
      console.error('Failed to toggle favorite:', error);
      // Revert all states if the backend call fails
      const revertChannelInState = (ch: Channel) => 
        ch.channel_number === channel.channel_number 
          ? { ...ch, isFavorite: channel.isFavorite }
          : ch;

      setChannels(prev => prev.map(revertChannelInState));
      setGroupChannels(prev => {
        const newState = { ...prev };
        Object.keys(newState).forEach(group => {
          if (newState[group]) {
            newState[group] = newState[group].map(revertChannelInState);
          }
        });
        return newState;
      });
    }
  };

  // Move refresh function definition before the useEffect
  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      await loadGroups();
      await loadChannels(false);
    } catch (error) {
      console.error('Failed to refresh channel list:', error);
    } finally {
      setLoading(false);
    }
  }, [loadGroups, loadChannels]);

  // Set the refresh function immediately when component mounts
  useEffect(() => {
    if (onRefresh) {
      onRefresh(refresh);
    }
    return () => {
      if (onRefresh) {
        onRefresh(undefined);
      }
    };
  }, [onRefresh, refresh]);

  // Update tab change handler to handle scroll position better
  const handleTabChange = (_: any, newValue: TabValue) => {
    // Change tab
    setActiveTab(newValue);
    
    // Reset search
    setSearchTerm('');
    setDebouncedSearchTerm('');

    // Load appropriate data for the new tab
    if (newValue === 'favorites') {
      loadChannels(false);
    } else if (newValue === 'recent') {
      const recentChannels = recentChannelsService.getRecentChannels();
      setChannels(recentChannels);
    } else if (newValue === 'all') {
      loadGroups();
    }
  };

  const handleToggleGroup = async (group: string) => {
    const isExpanding = !expandedGroups[group];
    const newExpandedGroups = {
      ...expandedGroups,
      [group]: !expandedGroups[group]
    };
    setExpandedGroups(newExpandedGroups);

    // Save expanded groups state for current tab
    localStorage.setItem(
      `channelListGroups_${activeTab}`, 
      JSON.stringify(newExpandedGroups)
    );

    // Load channels if expanding and not already loaded
    if (isExpanding && (!groupChannels[group] || groupChannels[group].length === 0)) {
      setLoading(true);
      try {
        const response = await channelService.getChannels(0, 1000, {
          group: group,
          search: debouncedSearchTerm,
          favoritesOnly: activeTab === 'favorites'
        });

        setGroupChannels(prev => ({
          ...prev,
          [group]: response.items
        }));

      } catch (error) {
        console.error('Failed to load channels for group:', error);
        // Revert expansion state on error
        setExpandedGroups(prev => ({
          ...prev,
          [group]: false
        }));
        localStorage.setItem(
          `channelListGroups_${activeTab}`,
          JSON.stringify({
            ...newExpandedGroups,
            [group]: false
          })
        );
      } finally {
        setLoading(false);
      }
    }
  };

  // Clean up the timeout on unmount
  useEffect(() => {
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, []);

  // Reload the favorites list when switching to the favorites tab
  useEffect(() => {
    if (activeTab === 'favorites') {
      loadChannels(false);
    }
  }, [activeTab, loadChannels]);

  const handleChannelSelect = (channel: Channel) => {
    // Add to recent channels
    recentChannelsService.addRecentChannel(channel);
    // Call the original onChannelSelect
    onChannelSelect(channel);
  };

  const handleScroll = useCallback((scrollOffset: number) => {
    localStorage.setItem(`channelListScroll_${activeTab}`, scrollOffset.toString());
    setTabStates(prev => ({
      ...prev,
      [activeTab]: {
        ...prev[activeTab],
        scrollPosition: scrollOffset
      }
    }));
  }, [activeTab]);

  return (
    <Paper elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 1 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Search channels..."
          value={searchTerm}
          onChange={(e) => {
            const newTerm = e.target.value;
            setSearchTerm(newTerm);
            
            // Clear any existing timeout
            if (searchTimeoutRef.current) {
              clearTimeout(searchTimeoutRef.current);
            }

            // Set new timeout for debounced search
            searchTimeoutRef.current = setTimeout(() => {
              initiateSearch(newTerm);
            }, 1000);
          }}
          onBlur={() => initiateSearch(searchTerm)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              if (searchTimeoutRef.current) {
                clearTimeout(searchTimeoutRef.current);
              }
              initiateSearch(searchTerm);
            }
          }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
        {showChannelNumbers && (
          <TextField
            size="small"
            placeholder="Channel #"
            value={channelInput}
            onChange={(e) => setChannelInput(e.target.value)}
            onKeyPress={handleChannelInput}
            sx={{ mt: 1, width: '100px' }}
          />
        )}
      </Box>

      <Tabs
        value={activeTab}
        onChange={handleTabChange}  // Use the new handler
        variant="fullWidth"
      >
        <Tab label="All" value="all" />
        <Tab label="Favorites" value="favorites" />
        <Tab label="Recent" value="recent" />
      </Tabs>

      <Box sx={{ flexGrow: 1 }}>
        <VirtualizedChannelList
          items={virtualizedItems}
          expandedGroups={expandedGroups}
          onToggleGroup={handleToggleGroup}
          selectedChannel={selectedChannel}
          onChannelSelect={handleChannelSelect}
          onToggleFavorite={handleToggleFavorite}
          showChannelNumbers={showChannelNumbers}
          initialScrollOffset={tabStates[activeTab].scrollPosition}
          onScroll={handleScroll}
        />
      </Box>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
          <CircularProgress size={24} />
        </Box>
      )}
    </Paper>
  );
}; 

export type { ChannelListProps }; 