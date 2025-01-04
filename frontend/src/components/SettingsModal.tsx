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
    showChannelNumbers: false,
    m3uUrl: '',
    updateInterval: 24,
    updateOnStart: true,
    theme: 'dark'
  });

  useEffect(() => {
    if (settings) {
      setFormState(settings);
    }
  }, [settings]);

  const [loading, setLoading] = useState(false);

  const handleRefreshClick = async () => {
    setLoading(true);
    try {
      await channelService.refreshM3U(formState.m3uUrl);
    } catch (error) {
      console.error('Failed to refresh channels:', error);
    } finally {
      setLoading(false);
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
            <IconButton
              onClick={handleRefreshClick}
              edge="end"
              sx={{ ml: 1 }}
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
            <IconButton
              onClick={() => console.log('Refresh EPG URL')}
              edge="end"
              sx={{ ml: 1 }}
            >
              <RefreshIcon />
            </IconButton>
          </Box>
          
          <TextField
            label="Update Interval (hours)"
            type="number"
            fullWidth
            value={formState.updateInterval}
            onChange={(e) => setFormState({ ...formState, updateInterval: Number(e.target.value) })}
          />
          
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
            onClick={() => onSave(formState)} 
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