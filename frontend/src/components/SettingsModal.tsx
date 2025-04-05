import React, { useState, useEffect } from "react";
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
  Typography,
  Tabs,
  Tab,
  Alert,
  Autocomplete,
} from "@mui/material";
import { Settings } from "../models/Settings";
import RefreshIcon from "@mui/icons-material/Refresh";
import { channelService } from "../services/channelService";
import Link from "@mui/material/Link";
import GitHubIcon from "@mui/icons-material/GitHub";
import RedditIcon from "@mui/icons-material/Reddit";
import { getUserTimezone } from "../utils/dateUtils";
import { defaultSettings } from "../services/settingsService";
import CloseIcon from "@mui/icons-material/Close";
import { ProgressDialog } from './ProgressDialog';

// Add timezone list - these are IANA timezone names
const TIMEZONES = Intl.supportedValuesOf("timeZone");

interface SettingsModalProps {
  open: boolean;
  onClose: () => void;
  settings: Settings;
  onSave: (settings: Settings) => Promise<void>;
  onM3uProgress?: (
    current: number,
    total: number | { type: "complete" },
  ) => void;
  onEpgProgress?: (
    current: number,
    total: number | { type: "complete" },
  ) => void;
  channelCount?: number;
  programCount?: number;
  onProgramReset?: () => Promise<void>;
}

// First, let's define a proper type for the progress message
interface ProgressMessage {
  type: 'progress' | 'complete';
  current?: number;
  total?: number;
  message?: string;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  open,
  onClose,
  settings,
  onSave,
  onM3uProgress,
  onEpgProgress,
  channelCount = 0,
  programCount = 0,
  onProgramReset,
}) => {
  const [formState, setFormState] = useState<Settings>({
    ...defaultSettings,
  });

  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    if (settings) {
      setFormState(settings);
    }
  }, [settings]);

  const [loading, setLoading] = useState(false);
  const [epgLoading, setEpgLoading] = useState(false);

  const [isResetting, setIsResetting] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);

  const [progressDialog, setProgressDialog] = useState<{
    open: boolean;
    title: string;
    message: string;
    progress?: number;
  }>({
    open: false,
    title: '',
    message: '',
    progress: undefined,
  });

  const handleM3uRefreshClick = async () => {
    setLoading(true);
    setProgressDialog({
      open: true,
      title: 'Refreshing M3U',
      message: 'Preparing to refresh...',
    });

    try {
      await channelService.refreshM3U(
        formState.m3uUrl,
        formState.m3uUpdateInterval,
        true,
        (current: number, total: number | ProgressMessage) => {
          // Check if total is a progress message object
          if (typeof total === 'object' && 'type' in total) {
            if (total.type === 'complete') {
              setProgressDialog(prev => ({
                ...prev,
                open: false,
              }));
            } else {
              setProgressDialog(prev => ({
                ...prev,
                open: true,
                message: total.message || 'Processing...',
                progress: total.total ? (current / total.total) * 100 : 0,
              }));
            }
          } else {
            // Handle numeric total (download progress)
            setProgressDialog(prev => ({
              ...prev,
              open: true,
              message: `Downloading M3U (${Math.round((current / total) * 100)}%)`,
              progress: (current / total) * 100,
            }));
          }
          // Still call the original progress handler
          onM3uProgress?.(current, total);
        },
      );
    } catch (error) {
      console.error("Failed to refresh channels:", error);
    } finally {
      setLoading(false);
      setProgressDialog(prev => ({
        ...prev,
        open: false,
      }));
    }
  };

  const handleEpgRefreshClick = async () => {
    if (!formState.epgUrl) {
      console.warn("No EPG URL provided");
      return;
    }

    setEpgLoading(true);
    setProgressDialog({
      open: true,
      title: 'Refreshing EPG',
      message: 'Preparing to refresh...',
    });

    try {
      await channelService.refreshEPG(
        formState.epgUrl,
        formState.epgUpdateInterval,
        true,
        (current: number, total: number | ProgressMessage) => {
          // Check if total is a progress message object
          if (typeof total === 'object' && 'type' in total) {
            if (total.type === 'complete') {
              setProgressDialog(prev => ({
                ...prev,
                open: false,
              }));
            } else {
              setProgressDialog(prev => ({
                ...prev,
                open: true,
                message: total.message || 'Processing...',
                progress: total.total ? (current / total.total) * 100 : 0,
              }));
            }
          } else {
            // Handle numeric total (download progress)
            setProgressDialog(prev => ({
              ...prev,
              open: true,
              message: total.message || `Downloading EPG (${Math.round((current / total) * 100)}%)`,
              progress: (current / total) * 100,
            }));
          }
          onEpgProgress?.(current, total);
        },
      );
    } catch (error) {
      console.error("Failed to refresh EPG:", error);
    } finally {
      setEpgLoading(false);
      setProgressDialog(prev => ({
        ...prev,
        open: false,
      }));
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
          onM3uProgress,
        );
      }

      // Refresh EPG if URL is provided
      if (formState.epgUrl) {
        onEpgProgress?.(0, 0);
        await channelService.refreshEPG(
          formState.epgUrl,
          formState.epgUpdateInterval,
          false, // don't force
          onEpgProgress,
        );
      }

      const updatedSettings: Settings = {
        ...formState,
        guideStartHour: Number(formState.guideStartHour),
        guideEndHour: Number(formState.guideEndHour),
        timezone: formState.timezone,
      };
      await onSave(updatedSettings);
      onClose();
    } catch (error) {
      console.error("Failed to save settings:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleHardReset = async () => {
    if (
      !window.confirm(
        "Are you sure you want to perform a hard reset? This will delete all channels and reload them from the M3U.",
      )
    ) {
      return;
    }

    setIsResetting(true);
    setResetError(null);
    try {
      await channelService.hardReset();
    } catch (error) {
      setResetError(
        error instanceof Error ? error.message : "Failed to reset channels",
      );
    } finally {
      setIsResetting(false);
    }
  };

  const handleProgramReset = async () => {
    if (!window.confirm(
      "Are you sure you want to perform a hard reset? This will delete all programs and reload them from the EPG."
    )) {
      return;
    }

    setIsResetting(true);
    setResetError(null);
    setProgressDialog({
      open: true,
      title: 'Resetting Programs',
      message: 'Preparing to reset...',
    });

    try {
      await channelService.hardResetPrograms((current, total) => {
        if ('type' in total && total.type === 'complete') {
          setProgressDialog(prev => ({
            ...prev,
            open: false,
          }));
        } else {
          setProgressDialog(prev => ({
            ...prev,
            message: `Inserting programs (${current}/${total})...`,
            progress: (current / (total as number)) * 100,
          }));
        }
        // Still call the original progress handler if it exists
        onEpgProgress?.(current, total);
      });
    } catch (error) {
      setResetError(
        error instanceof Error ? error.message : "Failed to reset programs"
      );
    } finally {
      setIsResetting(false);
      setProgressDialog(prev => ({
        ...prev,
        open: false,
      }));
    }
  };

  // Add tab panel component
  const TabPanel: React.FC<{
    children: React.ReactNode;
    value: number;
    index: number;
  }> = ({ children, value, index }) => (
    <Box sx={{ display: value === index ? "block" : "none", py: 2 }}>
      {children}
    </Box>
  );

  return (
    <>
      <Dialog
        open={open}
        onClose={formState.m3uUrl ? onClose : undefined}
        maxWidth="md"
        fullWidth
        disableEscapeKeyDown={!formState.m3uUrl}
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box sx={{ flexGrow: 1 }}>Settings</Box>
          <Typography variant="body2" color="text.secondary">
            {channelCount} Channels • {programCount} Programs
          </Typography>
          {formState.m3uUrl && (
            <IconButton
              aria-label="close"
              onClick={onClose}
              sx={{
                ml: 1,
              }}
            >
              <CloseIcon />
            </IconButton>
          )}
        </DialogTitle>
        <DialogContent sx={{ height: "80vh", overflow: "auto" }}>
          <Tabs
            value={activeTab}
            onChange={(_, newValue) => setActiveTab(newValue)}
            sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}
          >
            <Tab label="Settings" />
            <Tab label="Help" />
          </Tabs>

          <TabPanel value={activeTab} index={0}>
            <Stack spacing={3}>
              {!formState.m3uUrl && (
                <Box sx={{ mb: 2 }}>Please enter an M3U URL to get started.</Box>
              )}
              {/* M3U URL with Refresh Icon */}
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <TextField
                  label="M3U URL"
                  required
                  fullWidth
                  value={formState.m3uUrl}
                  onChange={(e) =>
                    setFormState({ ...formState, m3uUrl: e.target.value })
                  }
                  error={!formState.m3uUrl}
                  helperText={!formState.m3uUrl ? "M3U URL is required" : ""}
                />
                <TextField
                  label="Update Interval (hours)"
                  type="number"
                  sx={{ ml: 1, width: "300px" }}
                  value={formState.m3uUpdateInterval}
                  onChange={(e) =>
                    setFormState({
                      ...formState,
                      m3uUpdateInterval: Number(e.target.value),
                    })
                  }
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
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <TextField
                  label="EPG URL (Optional)"
                  fullWidth
                  value={formState.epgUrl}
                  onChange={(e) =>
                    setFormState({ ...formState, epgUrl: e.target.value })
                  }
                />
                <TextField
                  label="Update Interval (hours)"
                  type="number"
                  sx={{ ml: 1, width: "300px" }}
                  value={formState.epgUpdateInterval}
                  onChange={(e) =>
                    setFormState({
                      ...formState,
                      epgUpdateInterval: Number(e.target.value),
                    })
                  }
                />
                <IconButton
                  onClick={handleEpgRefreshClick}
                  edge="end"
                  sx={{ ml: 1 }}
                  title="Force EPG Refresh"
                >
                  {epgLoading ? <CircularProgress size={24} /> : <RefreshIcon />}
                </IconButton>
              </Box>

              <FormControlLabel
                control={
                  <Switch
                    checked={formState.updateOnStart}
                    onChange={(e) =>
                      setFormState({
                        ...formState,
                        updateOnStart: e.target.checked,
                      })
                    }
                  />
                }
                label="Update on App Start"
              />

              <FormControl fullWidth>
                <InputLabel>Theme</InputLabel>
                <Select
                  value={formState.theme}
                  onChange={(e) => {
                    const newTheme = e.target.value as
                      | "light"
                      | "dark"
                      | "system";
                    setFormState({ ...formState, theme: newTheme });
                  }}
                >
                  <MenuItem value="light">Light</MenuItem>
                  <MenuItem value="dark">Dark</MenuItem>
                  <MenuItem value="system">System</MenuItem>
                </Select>
              </FormControl>

              <Box sx={{ display: "flex", gap: 2, mt: 2 }}>
                <TextField
                  label="Recent Days"
                  type="number"
                  value={formState.recentDays}
                  onChange={(e) =>
                    setFormState({
                      ...formState,
                      recentDays: Math.max(
                        1,
                        Math.min(30, Number(e.target.value)),
                      ),
                    })
                  }
                  inputProps={{
                    min: 1,
                    max: 30,
                    step: 1,
                  }}
                  fullWidth
                  helperText="Days to show in Recent tab"
                />
                <TextField
                  label="Program Retention"
                  type="number"
                  value={formState.programRetentionHours}
                  onChange={(e) =>
                    setFormState({
                      ...formState,
                      programRetentionHours: Math.max(
                        1,
                        Math.min(24, Number(e.target.value)),
                      ),
                    })
                  }
                  inputProps={{
                    min: 1,
                    max: 24,
                    step: 1,
                  }}
                  fullWidth
                  helperText="Hours to keep ended programs"
                />
                <TextField
                  label="Guide Start Hour"
                  type="number"
                  value={formState.guideStartHour}
                  onChange={(e) =>
                    setFormState({
                      ...formState,
                      guideStartHour: Math.max(
                        -24,
                        Math.min(0, Number(e.target.value)),
                      ),
                    })
                  }
                  inputProps={{ min: -24, max: 0 }}
                  fullWidth
                  helperText="Hours before now (negative)"
                />
                <TextField
                  label="Guide End Hour"
                  type="number"
                  value={formState.guideEndHour}
                  onChange={(e) =>
                    setFormState({
                      ...formState,
                      guideEndHour: Math.max(
                        1,
                        Math.min(48, Number(e.target.value)),
                      ),
                    })
                  }
                  inputProps={{ min: 1, max: 48 }}
                  fullWidth
                  helperText="Hours after now"
                />
              </Box>

              {/* Add Timezone Selection */}
              <Autocomplete
                value={formState.timezone || getUserTimezone()}
                onChange={(_, newValue) => {
                  setFormState((prev) => ({
                    ...prev,
                    timezone: newValue || getUserTimezone(),
                  }));
                }}
                options={TIMEZONES}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Timezone"
                    helperText="Defaults to browser timezone if not set"
                  />
                )}
                disableClearable
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={formState.use24Hour}
                    onChange={(e) =>
                      setFormState({
                        ...formState,
                        use24Hour: e.target.checked,
                      })
                    }
                  />
                }
                label="Use 24-hour time format"
              />

              <Button
                variant="contained"
                onClick={handleSave}
                fullWidth
                disabled={!formState.m3uUrl}
              >
                Save Settings
              </Button>
            </Stack>
          </TabPanel>

          <TabPanel value={activeTab} index={1}>
            <Stack spacing={3}>
              <Typography variant="h6" gutterBottom>
                Community & Support
              </Typography>
              <Link
                href="https://github.com/Jacob-Lasky/iseetv"
                target="_blank"
                rel="noopener noreferrer"
                sx={{ display: "flex", alignItems: "center", gap: 1 }}
              >
                <GitHubIcon /> GitHub Project Page
              </Link>
              <Link
                href="https://reddit.com/r/iseetv"
                target="_blank"
                rel="noopener noreferrer"
                sx={{ display: "flex", alignItems: "center", gap: 1 }}
              >
                <RedditIcon /> ISeeTV Subreddit
              </Link>

              <Box sx={{ mt: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Hard Reset
                </Typography>
                <Typography paragraph>
                  If you are experiencing issues, you can perform a hard reset
                  which will delete all channels/programs and reload them from
                  your M3U/EPG file.
                </Typography>
                {resetError && (
                  <Alert severity="error" sx={{ mb: 2 }}>
                    {resetError}
                  </Alert>
                )}
                <Stack direction="row" spacing={2}>
                  <Button
                    variant="contained"
                    color="error"
                    onClick={handleHardReset}
                    disabled={isResetting}
                    startIcon={isResetting ? <CircularProgress size={20} /> : null}
                  >
                    {isResetting ? "Resetting..." : "Hard Reset Channels"}
                  </Button>
                  <Button
                    variant="contained"
                    color="error"
                    onClick={handleProgramReset}
                    disabled={!formState.epgUrl || isResetting}
                  >
                    Hard Reset Programs
                  </Button>
                </Stack>
              </Box>
            </Stack>
          </TabPanel>
        </DialogContent>
      </Dialog>
      <ProgressDialog
        open={progressDialog.open}
        title={progressDialog.title}
        message={progressDialog.message}
        progress={progressDialog.progress}
      />
    </>
  );
};
