import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  TextField,
  FormControlLabel,
  Switch,
  Button,
  Stack,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  CircularProgress,
  Box,
} from '@mui/material';
import { Settings } from '../models/Settings';
import RefreshIcon from '@mui/icons-material/Refresh';
import { channelService } from '../services/channelService';

interface SettingsModalProps {
  open: boolean;
  onClose: () => void;
  settings: Settings;
  onSave: (settings: Settings) => void;
  onThemeChange?: (theme: 'light' | 'dark' | 'system') => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  open,
  onClose,
  settings,
  onSave,
  onThemeChange,
}) => {
  const [formState, setFormState] = useState<Settings>({
    m3uUrl: '',
    m3uUpdateInterval: 24,
    epgUrl: '',
    epgUpdateInterval: 24,
    updateOnStart: true,
    theme: 'dark'
  });

  useEffect(() => {
    if (settings) {
      setFormState(settings);
    }
  }, [settings]);

  const [loading, setLoading] = useState(false);

  const handleM3uRefreshClick = async () => {
    setLoading(true);
    try {
      await channelService.refreshM3U(formState.m3uUrl, formState.m3uUpdateInterval, true);
    } catch (error) {
      console.error('Failed to refresh channels:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEpgRefreshClick = async () => {
    if (!formState.epgUrl) {
      console.warn('No EPG URL provided');
      return;
    }

    setLoading(true);
    try {
      await channelService.refreshEPG(formState.epgUrl, formState.epgUpdateInterval, true);
    } catch (error) {
      console.error('Failed to refresh EPG:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      await channelService.saveSettings(formState);
      onSave(formState);
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
  };

  return (
    <Dialog 
      open={open} 
      onClose={settings.m3uUrl ? onClose : undefined}
      maxWidth="sm" 
      fullWidth
    >
      <DialogTitle>Settings</DialogTitle>
      <DialogContent>
        <Stack spacing={3} sx={{ mt: 2 }}>
          {/* M3U URL with Refresh Icon */}
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <TextField
              label="M3U URL"
              required
              fullWidth
              value={formState.m3uUrl}
              onChange={(e) => setFormState({ ...formState, m3uUrl: e.target.value })}
              error={!formState.m3uUrl}
              helperText={!formState.m3uUrl ? "M3U URL is required" : ""}
            />
            <TextField
              label="Update Interval (hours)"
              type="number"
              sx={{ ml: 1, width: '300px' }}
              value={formState.m3uUpdateInterval}
              onChange={(e) => setFormState({ ...formState, m3uUpdateInterval: Number(e.target.value) })}
            />
            <IconButton
              onClick={handleM3uRefreshClick}
              edge="end"
              sx={{ ml: 1 }}
              title="Force M3U Refresh"
            >
              {loading ? <CircularProgress size={24} /> : <RefreshIcon />}
            </IconButton>
          </Box>
          
          {/* EPG URL with Refresh Icon */}
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <TextField
              label="EPG URL (Optional)"
              fullWidth
              value={formState.epgUrl}
              onChange={(e) => setFormState({ ...formState, epgUrl: e.target.value })}
            />
            <TextField
              label="Update Interval (hours)"
              type="number"
              sx={{ ml: 1, width: '300px' }}
              value={formState.epgUpdateInterval}
              onChange={(e) => setFormState({ ...formState, epgUpdateInterval: Number(e.target.value) })}
            />
            <IconButton
              onClick={handleEpgRefreshClick}
              edge="end"
              sx={{ ml: 1 }}
              title="Force EPG Refresh"
            >
              <RefreshIcon />
            </IconButton>
          </Box>
          
          <FormControlLabel
            control={
              <Switch
                checked={formState.updateOnStart}
                onChange={(e) => setFormState({ ...formState, updateOnStart: e.target.checked })}
              />
            }
            label="Update on App Start"
          />
          
          <FormControl fullWidth>
            <InputLabel>Theme</InputLabel>
            <Select
              value={formState.theme}
              onChange={(e) => {
                const newTheme = e.target.value as 'light' | 'dark' | 'system';
                setFormState({ ...formState, theme: newTheme });
                onThemeChange?.(newTheme);
              }}
            >
              <MenuItem value="light">Light</MenuItem>
              <MenuItem value="dark">Dark</MenuItem>
              <MenuItem value="system">System</MenuItem>
            </Select>
          </FormControl>
          
          <Button 
            variant="contained" 
            onClick={handleSave}
            fullWidth
            disabled={!formState.m3uUrl}
          >
            Save Settings
          </Button>
        </Stack>
      </DialogContent>
    </Dialog>
  );
}; 