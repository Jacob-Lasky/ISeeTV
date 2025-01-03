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

// Add a debounce utility at the top of the file
const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
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
  const [initialLoading, setInitialLoading] = useState(true);
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

    console.log('Filtered Channels:', filtered); // Debugging line

    return filtered;
  }, [channels, debouncedSearchTerm, activeTab]);

  const virtualizedItems = React.useMemo(() => {
    // If searching in any tab, show filtered channels directly
    if (debouncedSearchTerm) {
      // If we're in "all" tab and searching, load all channels
      if (activeTab === 'all') {
        // Flatten all channels from groupChannels
        const allChannels = Object.values(groupChannels).flat();
        return allChannels.filter(c => 
          c.name.toLowerCase().includes(debouncedSearchTerm.toLowerCase()) ||
          c.channel_number.toString().includes(debouncedSearchTerm)
        );
      }
      return filteredChannels;
    }

    // If not searching, handle normal tab behavior
    if (activeTab === 'all') {
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
          favoritesOnly: activeTab === 'favorites'
        }
      );

      if (activeTab === 'all') {
        // Update groupChannels with the search results
        const newGroupChannels: Record<string, Channel[]> = {};
        response.items.forEach(channel => {
          const group = channel.group || 'Uncategorized';
          if (!newGroupChannels[group]) {
            newGroupChannels[group] = [];
          }
          newGroupChannels[group].push(channel);
        });
        setGroupChannels(newGroupChannels);
      } else {
        setChannels(response.items);
      }
    } catch (error) {
      console.error('Failed to load channels:', error);
    } finally {
      setLoading(false);
    }
  }, [debouncedSearchTerm, activeTab]);

  const loadGroupChannelsIfNeeded = useCallback(async (expandedGroupNames: string[]) => {
    if (expandedGroupNames.length === 0) return;

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
  }, []);

  const loadGroups = useCallback(async () => {
    if (groups.length > 0) return;
  
    try {
      // Load groups
      const groups = await channelService.getGroups();
      setGroups(groups);
      
      const savedExpandedGroups = JSON.parse(
        localStorage.getItem(`channelListGroups_${activeTab}`) || '{}'
      );
      
      // Pre-fetch channels for all groups in parallel
      const groupPromises = groups.map(group => 
        channelService.getChannels(0, 1000, { group: group.name })
      );
      
      const responses = await Promise.all(groupPromises);
      
      // Update group channels all at once
      const newGroupChannels: Record<string, Channel[]> = {};
      groups.forEach((group, index) => {
        newGroupChannels[group.name] = responses[index].items;
      });
      
      setGroupChannels(newGroupChannels);
      setExpandedGroups(savedExpandedGroups);
      
    } catch (error) {
      console.error('Failed to load groups and channels:', error);
    }
  }, [activeTab, groups.length]);

  // Update the initialization effect
  useEffect(() => {
    let mounted = true;

    const initializeList = async () => {
      if (!mounted) return;
      
      setInitialLoading(true);
      try {
        if (activeTab === 'all') {
          await loadGroups();
        } else if (activeTab === 'favorites') {
          await loadChannels(false);
        } else if (activeTab === 'recent') {
          const recentChannels = recentChannelsService.getRecentChannels();
          setChannels(recentChannels);
        }
      } finally {
        if (mounted) {
          setInitialLoading(false);
        }
      }
    };

    initializeList();

    return () => {
      mounted = false;
    };
  }, [activeTab, loadGroups, loadChannels]);

  const handleChannelInput = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      const channel = channels.find(c => c.guide_id === channelInput);
      if (channel) {
        handleChannelSelect(channel);
        setChannelInput('');
      }
    }
  };

  const handleToggleFavorite = async (channel: Channel) => {
    try {
      // Update UI optimistically
      const newFavoriteStatus = !channel.isFavorite;
      
      const updateChannelInState = (ch: Channel) => 
        ch.guide_id === channel.guide_id 
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

      // Call backend
      const updatedChannel = await channelService.toggleFavorite(channel.guide_id);

      // Update states with response
      setChannels(prev => prev.map(ch => 
        ch.guide_id === updatedChannel.guide_id 
          ? { ...ch, isFavorite: updatedChannel.isFavorite }
          : ch
      ));

      // If we're in favorites tab, refresh the list
      if (activeTab === 'favorites') {
        const response = await channelService.getChannels(0, 1000, {
          favoritesOnly: true
        });
        setChannels(response.items);
      }
      // If we're in all tab, update the group channels
      else if (activeTab === 'all') {
        // Update the channel in group channels
        setGroupChannels(prev => {
          const newState = { ...prev };
          Object.keys(newState).forEach(group => {
            if (newState[group]) {
              newState[group] = newState[group].map(ch =>
                ch.guide_id === updatedChannel.guide_id
                  ? { ...ch, isFavorite: updatedChannel.isFavorite }
                  : ch
              );
            }
          });
          return newState;
        });
      }

    } catch (error) {
      console.error('Failed to toggle favorite:', error);
      // Revert states on error
      const revertChannelInState = (ch: Channel) => 
        ch.guide_id === channel.guide_id 
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

  // Update the debounced refresh to return a Promise
  const debouncedRefresh = useCallback(
    () => new Promise<void>(resolve => {
      debounce(async () => {
        setLoading(true);
        try {
          if (activeTab === 'all') {
            await loadGroups();
          } else if (activeTab === 'favorites') {
            await loadChannels(false);
          } else if (activeTab === 'recent') {
            const recentChannels = recentChannelsService.getRecentChannels();
            setChannels(recentChannels);
          }
        } catch (error) {
          console.error('Failed to refresh channel list:', error);
        } finally {
          setLoading(false);
          resolve();
        }
      }, 500)();
    }),
    [activeTab, loadGroups, loadChannels]
  );

  // Use the debounced version in the component
  useEffect(() => {
    if (onRefresh) {
      onRefresh(debouncedRefresh);
    }
    return () => {
      if (onRefresh) {
        onRefresh(undefined);
      }
    };
  }, [onRefresh, debouncedRefresh]);

  // Update handleTabChange to preload data
  const handleTabChange = async (_: any, newValue: TabValue) => {
    // Load data before changing tab
    if (newValue === 'all') {
      // Get the expanded groups for the "all" tab
      const savedExpandedGroups = JSON.parse(
        localStorage.getItem(`channelListGroups_${newValue}`) || '{}'
      );
      
      // Load groups first
      await loadGroups();
      
      // Load channels for expanded groups
      const expandedGroupNames = Object.entries(savedExpandedGroups)
        .filter(([_, isExpanded]) => isExpanded)
        .map(([groupName]) => groupName);
        
      await loadGroupChannelsIfNeeded(expandedGroupNames);
      
      // Set expanded state after data is loaded
      setExpandedGroups(savedExpandedGroups);
    } else if (newValue === 'favorites') {
      await loadChannels(false);
    } else if (newValue === 'recent') {
      const recentChannels = recentChannelsService.getRecentChannels();
      setChannels(recentChannels);
    }

    // Change tab after data is loaded
    setActiveTab(newValue);
    
    // Reset search
    setSearchTerm('');
    setDebouncedSearchTerm('');
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

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTerm = e.target.value;
    setSearchTerm(newTerm);

    // Clear any existing timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    // Set new timeout for debounced search
    searchTimeoutRef.current = setTimeout(() => {
      setDebouncedSearchTerm(newTerm);
      // Load channels when search term changes
      if (activeTab === 'all') {
        loadChannels(false);
      }
    }, 300);
  };

  return (
    <Paper elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 1 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Search channels..."
          value={searchTerm}
          onChange={handleSearchChange}
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
        {initialLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <CircularProgress />
          </Box>
        ) : (
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
        )}
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