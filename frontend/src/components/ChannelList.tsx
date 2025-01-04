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
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { Channel } from '../models/Channel';
import { channelService } from '../services/channelService';
import { ChannelGroup } from '../types/api';
import { recentChannelsService } from '../services/recentChannelsService';
import { FixedSizeList } from 'react-window';
import AutoSizer from 'react-virtualized-auto-sizer';
import { useNavigate } from 'react-router-dom';

export {};

interface ChannelListProps {
  selectedChannel?: Channel;
  onChannelSelect: (channel: Channel) => void;
  onToggleFavorite: (channel: Channel) => void;
  onRefresh?: (refreshFn: (() => Promise<void>) | undefined) => void;
  onOpenSettings?: () => void;
}

type TabValue = 'all' | 'favorites' | 'recent';

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
  initialScrollOffset = 0,
  onScroll,
}) => {
  const listRef = useRef<FixedSizeList>(null);
  const navigate = useNavigate();

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
          onClick={(e) => {
            e.stopPropagation();
            onToggleGroup(item.name);
          }}
          style={style}
        >
          <ListItemText primary={`${item.name} (${item.count})`} />
          {expandedGroups[item.name] ? <ExpandLess /> : <ExpandMore />}
        </ListItemButton>
      );
    }
    
    // Channel item
    return (
      <ListItemButton
        onClick={() => {
          onChannelSelect(item);
          navigate(`/channel/${item.guide_id}`);
        }}
        style={style}
      >
        <IconButton
          size="small"
          onClick={(e) => {
            e.stopPropagation();
            onToggleFavorite(item);
          }}
          sx={{ mr: 1 }}
        >
          {item.isFavorite ? <StarIcon color="primary" /> : <StarBorderIcon />}
        </IconButton>
        <ListItemIcon>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Avatar
              src={item.logo}
              alt={item.name}
              variant="square"
              sx={{ width: 32, height: 32 }}
            >
              {item.name[0]}
            </Avatar>
          </Box>
        </ListItemIcon>
        <ListItemText primary={item.name} />
      </ListItemButton>
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
  onOpenSettings,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState<TabValue>('all');
  const [initialLoading, setLoading] = useState(true);
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
        c.name.toLowerCase().includes(search)
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
          c.name.toLowerCase().includes(debouncedSearchTerm.toLowerCase())
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
      const response = await channelService.getChannels(
        0,
        1000,
        {
          search: debouncedSearchTerm,
          favoritesOnly: activeTab === 'favorites'
        }
      );

      // Update both channels and groupChannels states
      if (activeTab === 'all') {
        const newGroupChannels: Record<string, Channel[]> = {};
        response.items.forEach(channel => {
          const group = channel.group || 'Uncategorized';
          if (!newGroupChannels[group]) {
            newGroupChannels[group] = [];
          }
          newGroupChannels[group].push(channel);
        });
        setGroupChannels(newGroupChannels);
      }
      
      setChannels(response.items);
      
    } catch (error) {
      console.error('Failed to load channels:', error);
    }
  }, [debouncedSearchTerm, activeTab]);

  const loadGroups = useCallback(async (forceReload = false) => {
    if (groups.length > 0 && !forceReload) return;

    try {
      // Load groups
      const groups = await channelService.getGroups();
      setGroups(groups);
      
      const savedExpandedGroups = JSON.parse(
        localStorage.getItem(`channelListGroups_${activeTab}`) || '{}'
      );
      
      // Only load channels for expanded groups
      const expandedGroupNames = Object.entries(savedExpandedGroups)
        .filter(([_, isExpanded]) => isExpanded)
        .map(([groupName]) => groupName);

      if (expandedGroupNames.length > 0) {
        const groupPromises = expandedGroupNames.map(groupName => 
          channelService.getChannels(
            0,
            10000,
            { 
              group: groupName,
              search: debouncedSearchTerm,
              favoritesOnly: activeTab === 'favorites'
            }
          )
        );
        
        const responses = await Promise.all(groupPromises);
        
        // Update only expanded group channels
        const newGroupChannels: Record<string, Channel[]> = {};
        expandedGroupNames.forEach((groupName, index) => {
          newGroupChannels[groupName] = responses[index].items;
        });
        
        setGroupChannels(newGroupChannels);
      }
      
      setExpandedGroups(savedExpandedGroups);
      
    } catch (error) {
      console.error('Failed to load groups and channels:', error);
    }
  }, [activeTab, groups.length, debouncedSearchTerm]);

  // Update the initialization effect
  useEffect(() => {
    let mounted = true;

    const initializeList = async () => {
      if (!mounted) return;
      
      setLoading(true);
      try {
        if (activeTab === 'all') {
          await loadGroups();
        } else if (activeTab === 'favorites') {
          await loadChannels(false);
        } else if (activeTab === 'recent') {
          // Get fresh data from backend
          const response = await channelService.getChannels(0, 1000);
          const freshChannels = response.items;
          
          // Get recent channels and update them with fresh data
          const recentChannels = recentChannelsService.getRecentChannels();
          const updatedRecentChannels = recentChannels.map(ch => {
            const freshChannel = freshChannels.find(f => f.guide_id === ch.guide_id);
            return freshChannel || ch;
          });
          
          // Update recent channels in storage and state
          recentChannelsService.updateRecentChannels(updatedRecentChannels);
          setChannels(updatedRecentChannels);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    initializeList();

    return () => {
      mounted = false;
    };
  }, [activeTab, loadGroups, loadChannels]);

  const handleToggleFavorite = async (channel: Channel) => {
    const originalFavoriteStatus = channel.isFavorite;
    
    try {
      const newFavoriteStatus = !originalFavoriteStatus;
      
      // Update UI optimistically
      setChannels(prev => prev.map(ch => 
        ch.guide_id === channel.guide_id 
          ? { ...ch, isFavorite: newFavoriteStatus }
          : ch
      ));

      setGroupChannels(prev => {
        const newState = { ...prev };
        Object.keys(newState).forEach(group => {
          if (newState[group]) {
            newState[group] = newState[group].map(ch =>
              ch.guide_id === channel.guide_id 
                ? { ...ch, isFavorite: newFavoriteStatus }
                : ch
            );
          }
        });
        return newState;
      });

      // Call backend
      await onToggleFavorite(channel);

      // Refresh all relevant states
      if (activeTab === 'all') {
        await loadGroups(true); // Pass true to force reload
      } else if (activeTab === 'favorites') {
        await loadChannels(false);
      } else if (activeTab === 'recent') {
        // Get fresh data from backend
        const response = await channelService.getChannels(0, 1000);
        const freshChannels = response.items;
        
        // Get recent channels and update them with fresh data
        const recentChannels = recentChannelsService.getRecentChannels();
        const updatedRecentChannels = recentChannels.map(ch => {
          const freshChannel = freshChannels.find(f => f.guide_id === ch.guide_id);
          return freshChannel || ch;
        });
        
        // Update recent channels in storage and state
        recentChannelsService.updateRecentChannels(updatedRecentChannels);
        setChannels(updatedRecentChannels);
      }

    } catch (error) {
      console.error('Failed to toggle favorite:', error);
      // Revert UI changes
      setChannels(prev => prev.map(ch => 
        ch.guide_id === channel.guide_id 
          ? { ...ch, isFavorite: originalFavoriteStatus }
          : ch
      ));
      
      setGroupChannels(prev => {
        const newState = { ...prev };
        Object.keys(newState).forEach(group => {
          if (newState[group]) {
            newState[group] = newState[group].map(ch =>
              ch.guide_id === channel.guide_id 
                ? { ...ch, isFavorite: originalFavoriteStatus }
                : ch
            );
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
    setLoading(true); // Show loading state while switching
    try {
      // Reset states first
      setChannels([]);
      setGroupChannels({});
      setExpandedGroups({});
      
      if (newValue === 'all') {
        // Force reload groups and their channels
        await loadGroups(true); // Pass true to force reload
        
        // Get and set expanded groups after data is loaded
        const savedExpandedGroups = JSON.parse(
          localStorage.getItem(`channelListGroups_${newValue}`) || '{}'
        );
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
    } finally {
      setLoading(false);
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
      <Box sx={{ p: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
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
        {onOpenSettings && (
          <IconButton onClick={onOpenSettings} size="small">
            <SettingsIcon />
          </IconButton>
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
            initialScrollOffset={tabStates[activeTab].scrollPosition}
            onScroll={handleScroll}
          />
        )}
      </Box>
    </Paper>
  );
}; 

export type { ChannelListProps }; 