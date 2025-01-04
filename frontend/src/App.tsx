import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Box, ThemeProvider, CssBaseline, Typography, IconButton } from '@mui/material';
import { createTheme } from '@mui/material/styles';
import { ChannelList } from './components/ChannelList';
import { VideoPlayer } from './components/VideoPlayer';
import { channelService } from './services/channelService';
import { SettingsModal } from './components/SettingsModal';
import type { Channel } from './models/Channel';
import { settingsService } from './services/settingsService';
import type { Settings } from './models/Settings';
import MenuIcon from '@mui/icons-material/Menu';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';

function App() {
  const [selectedChannel, setSelectedChannel] = useState<Channel | undefined>();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, setSettings] = useState<Settings>({
    m3uUrl: '',
    epgUrl: '',
    epgUpdateInterval: 24,
    m3uUpdateInterval: 24,
    updateOnStart: true,
    theme: 'dark'
  });
  const [channelListOpen, setChannelListOpen] = useState(true);
  
  useEffect(() => {
    // Load settings from backend
    const loadSettings = async () => {
      try {
        const loadedSettings = await channelService.getSettings();
        setSettings(loadedSettings);
      } catch (error) {
        console.error('Failed to load settings:', error);
      }
    };
    loadSettings();
  }, []);

  // Create theme based on settings
  const theme = createTheme({
    palette: {
      mode: settings.theme === 'system' 
        ? window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
        : settings.theme
    }
  });

  // Add system theme listener
  useEffect(() => {
    if (settings.theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = () => {
        setSettings(prev => ({ ...prev })); // Force re-render
      };
      
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [settings.theme]);

  const handleSaveSettings = (newSettings: Settings) => {
    setSettings(newSettings);
    settingsService.saveSettings(newSettings);
    setSettingsOpen(false);
  };

  const handleChannelSelect = (channel: Channel) => {
    setSelectedChannel(channel);
  };

  const handleToggleFavorite = async (channel: Channel) => {
    await channelService.toggleFavorite(channel.guide_id);
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
          settings={settings}
          onSave={handleSaveSettings}
        />
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App; 