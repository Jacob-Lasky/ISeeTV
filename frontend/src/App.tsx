import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Box, ThemeProvider, CssBaseline, Typography, IconButton } from '@mui/material';
import { createTheme } from '@mui/material/styles';
import { ChannelList } from './components/ChannelList';
import { VideoPlayer } from './components/VideoPlayer';
import { channelService } from './services/channelService';
import { SettingsModal } from './components/SettingsModal';
import type { Channel } from './models/Channel';
import type { Settings } from './models/Settings';
import MenuIcon from '@mui/icons-material/Menu';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import { LoadingPopup } from './components/LoadingPopup';


// Interface for progress data state
interface ProgressData {
  current: number;
  total: number;
  message?: string;
}

// Interface for progress messages from backend
interface ProgressMessage {
  type: string;
  current?: number;
  total?: number;
  message?: string;
}

export default function App() {
  const [selectedChannel, setSelectedChannel] = useState<Channel | undefined>();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [channelListOpen, setChannelListOpen] = useState(true);
  const [m3uProgress, setM3uProgress] = useState<ProgressData | null>(null);
  const [epgProgress, setEpgProgress] = useState<ProgressData | null>(null);
  const channelListRef = useRef<{ refresh: () => Promise<void> }>(null);
  const [visibleChannels, setVisibleChannels] = useState<Channel[]>([]);
  const [programs, setPrograms] = useState<Record<string, Program[]>>({});
  
  useEffect(() => {
    const checkSettings = async () => {
      try {
        const loadedSettings = await channelService.getSettings();
        setSettings(loadedSettings);
        
        // Show settings modal if no M3U URL
        if (!loadedSettings.m3uUrl) {
          setSettingsOpen(true);
          return;
        }

        // If updateOnStart is enabled, refresh both M3U and EPG
        if (loadedSettings.updateOnStart) {
          // Refresh M3U
          await channelService.refreshM3U(
            loadedSettings.m3uUrl,
            loadedSettings.m3uUpdateInterval,
            false,
            handleM3uProgress
          );
          await channelListRef.current?.refresh();

          // Refresh EPG if URL is provided
          if (loadedSettings.epgUrl) {
            await channelService.refreshEPG(
              loadedSettings.epgUrl,
              loadedSettings.epgUpdateInterval,
              false,
              handleEpgProgress
            );
          }
        }
      } catch (error) {
        console.error('Failed to load settings:', error);
        setSettingsOpen(true);
      }
    };

    checkSettings();
  }, []);

  // Create theme based on settings
  const theme = createTheme({
    palette: {
      mode: settings?.theme === 'system' 
        ? window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
        : settings?.theme ?? 'dark'
    }
  });

  // Add system theme listener
  useEffect(() => {
    if (settings?.theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = () => {
        setSettings(prev => prev ? { ...prev } : null);
      };
      
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [settings?.theme]);

  const handleSaveSettings = async (newSettings: Settings) => {
    try {
      setSettings(newSettings);
      await channelService.saveSettings(newSettings);
      
      // Refresh channels after saving settings
      if (newSettings.m3uUrl) {
        await channelService.refreshM3U(
          newSettings.m3uUrl,
          newSettings.m3uUpdateInterval,
          false,
          handleM3uProgress
        );
        // Refresh channel list after M3U download
        await channelListRef.current?.refresh();
      }

      if (newSettings.epgUrl) {
        await channelService.refreshEPG(
          newSettings.epgUrl,
          newSettings.epgUpdateInterval,
          false,
          handleEpgProgress
        );
      }
      
      setSettingsOpen(false);
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
  };

  const handleChannelSelect = (channel: Channel) => {
    setSelectedChannel(channel);
  };

  const handleToggleFavorite = async (channel: Channel) => {
    await channelService.toggleFavorite(channel.guide_id);
  };

  const handleM3uProgress = (current: number, total: number | ProgressMessage) => {
    if (typeof total === 'object' && total.type === 'complete') {
      setM3uProgress(null);
    } else if (typeof total === 'number') {
      setM3uProgress({ 
        current, 
        total,
        message: undefined
      });
    } else if (typeof total === 'object') {
      setM3uProgress({ 
        current, 
        total: total.current || 0,
        message: total.message
      });
    }
  };

  const handleEpgProgress = (current: number, total: number | ProgressMessage) => {
    if (typeof total === 'object' && total.type === 'complete') {
      setEpgProgress(null);
    } else if (typeof total === 'number') {
      setEpgProgress({ 
        current, 
        total,
        message: undefined
      });
    } else if (typeof total === 'object') {
      setEpgProgress({ 
        current, 
        total: total.current || 0,
        message: total.message
      });
    }
  };

  // Update channel list toggle to preserve EPG state
  const handleChannelListToggle = () => {
    setChannelListOpen(prev => !prev); // Simply toggle the channel list state
  };

  // Add effect to fetch programs
  useEffect(() => {
    const fetchPrograms = async () => {
      if (visibleChannels.length > 0) {
        try {
          const startTime = getStartTime();
          const endTime = new Date(startTime);
          endTime.setHours(endTime.getHours() + 4);

          const guideIds = visibleChannels.map(c => c.guide_id);
          const programData = await channelService.getPrograms(guideIds, startTime, endTime);
          setPrograms(programData);
        } catch (error) {
          console.error('Failed to fetch programs:', error);
        }
      }
    };

    fetchPrograms();
  }, [visibleChannels]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Box sx={{ 
          display: 'flex', 
          height: '100vh',
          width: '100vw',
          overflow: 'hidden',
          position: 'relative'
        }}>
          <Box sx={{ 
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: 'auto',
            minWidth: 300,
            maxWidth: channelListOpen ? '80vw' : 0,
            transform: channelListOpen ? 'none' : 'translateX(-100%)',
            transition: theme.transitions.create(['transform', 'max-width'], {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
            zIndex: 2
          }}>
            <ChannelList 
              ref={channelListRef}
              onChannelSelect={handleChannelSelect}
              onToggleFavorite={handleToggleFavorite}
              selectedChannel={selectedChannel}
              onOpenSettings={() => setSettingsOpen(true)}
              onChannelsChange={setVisibleChannels}
              programs={programs}
              channelListOpen={channelListOpen}
            />
          </Box>

          <Box sx={{ 
            position: 'absolute',
            left: channelListOpen ? 300 : 0,
            right: 0,  // Keep right edge fixed
            top: 0,
            bottom: 0,
            transition: theme.transitions.create('left', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            })
          }}>
            <IconButton
              onClick={handleChannelListToggle}
              sx={{
                position: 'fixed',
                left: channelListOpen ? 300 : 0,
                top: 8,
                zIndex: 3,
                bgcolor: 'background.paper',
                borderRadius: '0 4px 4px 0',
                transition: theme.transitions.create('left', {
                  easing: theme.transitions.easing.sharp,
                  duration: theme.transitions.duration.enteringScreen,
                }),
                '&:hover': {
                  bgcolor: 'action.hover',
                }
              }}
            >
              {channelListOpen ? <ChevronLeftIcon /> : <MenuIcon />}
            </IconButton>

            <Routes>
              <Route path="/" element={
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                  <Typography variant="h6" color="text.secondary">
                    Select a channel to begin
                  </Typography>
                </Box>
              } />
              <Route path="/channel/:channelId" element={
                selectedChannel ? 
                  <VideoPlayer 
                    url={selectedChannel.url} 
                    channel={selectedChannel}
                  /> : 
                  <Navigate to="/" replace />
              } />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Box>
        </Box>
        <SettingsModal 
          open={settingsOpen} 
          onClose={() => setSettingsOpen(false)}
          settings={settings ?? {
            m3uUrl: '',
            epgUrl: '',
            epgUpdateInterval: 24,
            m3uUpdateInterval: 24,
            updateOnStart: true,
            theme: 'dark'
          }}
          onSave={handleSaveSettings}
          onM3uProgress={handleM3uProgress}
          onEpgProgress={handleEpgProgress}
        />
        <LoadingPopup 
          m3uProgress={m3uProgress}
          epgProgress={epgProgress}
        />
      </BrowserRouter>
    </ThemeProvider>
  );
} 