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
import { DownloadProgress } from './components/DownloadProgress';

export default function App() {
  const [selectedChannel, setSelectedChannel] = useState<Channel | undefined>();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [channelListOpen, setChannelListOpen] = useState(true);
  const [m3uProgress, setM3uProgress] = useState<{ current: number; total: number } | null>(null);
  const [epgProgress, setEpgProgress] = useState<{ current: number; total: number } | null>(null);
  const channelListRef = useRef<{ refresh: () => Promise<void> }>(null);
  
  useEffect(() => {
    const checkSettings = async () => {
      try {
        const loadedSettings = await channelService.getSettings();
        setSettings(loadedSettings);
        // Show settings modal if no M3U URL
        if (!loadedSettings.m3uUrl) {
          setSettingsOpen(true);
        }
      } catch (error) {
        console.error('Failed to load settings:', error);
        setSettingsOpen(true); // Show settings on error too
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

  const handleM3uProgress = (current: number, total: number) => {
    setM3uProgress({ current, total });
    
    // Clear progress after completion
    if (current === total && total > 0) {
      setTimeout(() => setM3uProgress(null), 2000);
    }
  };

  const handleEpgProgress = (current: number, total: number) => {
    setEpgProgress({ current, total });
    
    // Clear progress after completion
    if (current === total && total > 0) {
      setTimeout(() => setEpgProgress(null), 2000);
    }
  };

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
            width: 300,
            transform: channelListOpen ? 'none' : 'translateX(-300px)',
            transition: theme.transitions.create('transform', {
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
            />
          </Box>

          <Box sx={{ 
            flexGrow: 1,
            ml: channelListOpen ? '300px' : 0,
            transition: theme.transitions.create('margin', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            })
          }}>
            <IconButton
              onClick={() => setChannelListOpen(!channelListOpen)}
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
        {m3uProgress && (
          <DownloadProgress 
            type="M3U" 
            current={m3uProgress.current} 
            total={m3uProgress.total} 
          />
        )}
        {epgProgress && (
          <DownloadProgress 
            type="EPG" 
            current={epgProgress.current} 
            total={epgProgress.total} 
          />
        )}
      </BrowserRouter>
    </ThemeProvider>
  );
} 