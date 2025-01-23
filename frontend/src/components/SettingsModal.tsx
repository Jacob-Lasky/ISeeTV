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
  onSave: (settings: Settings) => Promise<void>;
  onM3uProgress?: (current: number, total: number | { type: 'complete' }) => void;
  onEpgProgress?: (current: number, total: number | { type: 'complete' }) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  open,
  onClose,
  settings,
  onSave,
  onM3uProgress,
  onEpgProgress,
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
    onM3uProgress?.(0, 0);
    
    try {
      await channelService.refreshM3U(
        formState.m3uUrl, 
        formState.m3uUpdateInterval, 
        true,
        onM3uProgress
      );
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
    onEpgProgress?.(0, 0);
    
    try {
      await channelService.refreshEPG(
        formState.epgUrl, 
        formState.epgUpdateInterval, 
        true,
        onEpgProgress
      );
    } catch (error) {
      console.error('Failed to refresh EPG:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      // Save settings first
      await channelService.saveSettings(formState);
      
      // Refresh M3U if URL is provided
      if (formState.m3uUrl) {
        setLoading(true);
        onM3uProgress?.(0, 0);
        await channelService.refreshM3U(
          formState.m3uUrl,
          formState.m3uUpdateInterval,
          false, // don't force
          onM3uProgress
        );
      }

      // Refresh EPG if URL is provided
      if (formState.epgUrl) {
        onEpgProgress?.(0, 0);
        await channelService.refreshEPG(
          formState.epgUrl,
          formState.epgUpdateInterval,
          false, // don't force
          onEpgProgress
        );
      }

      onSave(formState);
    } catch (error) {
      console.error('Failed to save settings:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog 
      open={open} 
      onClose={formState.m3uUrl ? onClose : undefined}
      maxWidth="sm" 
      fullWidth
      disableEscapeKeyDown={!formState.m3uUrl}
    >
      <DialogTitle>
        {!formState.m3uUrl ? 'Initial Setup Required' : 'Settings'}
      </DialogTitle>
      <DialogContent>
        <Stack spacing={3} sx={{ mt: 2 }}>
          {!formState.m3uUrl && (
            <Box sx={{ mb: 2 }}>
              Please enter an M3U URL to get started.
            </Box>
          )}
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