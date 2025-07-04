import React, { useState, useEffect, useRef } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import {
  Box,
  ThemeProvider,
  CssBaseline,
  Typography,
  IconButton,
  useMediaQuery,
} from "@mui/material";
import { createTheme } from "@mui/material/styles";
import { ChannelList } from "./components/ChannelList";
import { VideoPlayer } from "./components/VideoPlayer";
import { channelService } from "./services/channelService";
import { SettingsModal } from "./components/SettingsModal";
import type { Channel } from "./models/Channel";
import type { Settings } from "./models/Settings";
import { format } from "date-fns";
import MenuIcon from "@mui/icons-material/Menu";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import { LoadingPopup } from "./components/LoadingPopup";
import { getTodayOffsetDate, getUserTimezone } from "./utils/dateUtils";
import { defaultSettings } from "./services/settingsService";

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

// Add Program interface
interface Program {
  start: string;
  stop: string;
  title: string;
  desc?: string;
}

export default function App() {
  const [selectedChannel, setSelectedChannel] = useState<Channel | undefined>();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, setSettings] = useState<Settings>(defaultSettings);
  const [channelListOpen, setChannelListOpen] = useState(true);
  const [m3uProgress, setM3uProgress] = useState<ProgressData | null>(null);
  const [epgProgress, setEpgProgress] = useState<ProgressData | null>(null);
  const channelListRef = useRef<{ refresh: () => Promise<void> }>(null);
  const [programs, setPrograms] = useState<Record<string, Program[]>>({});
  const [programsLoading, setProgramsLoading] = useState(true);

  // Create theme based on settings
  const theme = createTheme({
    palette: {
      mode:
        settings?.theme === "system"
          ? window.matchMedia("(prefers-color-scheme: dark)").matches
            ? "dark"
            : "light"
          : (settings?.theme ?? "dark"),
    },
  });

  // Move useMediaQuery after theme creation
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  // Combine initial data loading into one effect
  useEffect(() => {
    const initializeApp = async () => {
      try {
        const loadedSettings = await channelService.getSettings();
        setSettings({
          ...defaultSettings,
          ...loadedSettings,
          timezone: loadedSettings.timezone || getUserTimezone(),
        });

        if (!loadedSettings.m3uUrl) {
          setSettingsOpen(true);
          return;
        }

        // Only fetch programs if we need to update
        if (loadedSettings.updateOnStart) {
          await channelService.refreshM3U(
            loadedSettings.m3uUrl,
            loadedSettings.m3uUpdateInterval,
            false,
            handleM3uProgress,
          );

          if (loadedSettings.epgUrl) {
            await channelService.refreshEPG(
              loadedSettings.epgUrl,
              loadedSettings.epgUpdateInterval,
              false,
              handleEpgProgress,
            );
          }
        }

        // Fetch programs after potential refresh
        setProgramsLoading(true);
        const startTimeDate = getTodayOffsetDate(settings.guideStartHour);
        const endTimeDate = getTodayOffsetDate(settings.guideEndHour);
        const startTime = format(startTimeDate, "yyyy-MM-dd'T'HH:mm:ss");
        const endTime = format(endTimeDate, "yyyy-MM-dd'T'HH:mm:ss");
        console.debug("Fetching programs between", startTime, "and", endTime);
        console.debug("Converting programs to timezone:", settings.timezone);
        const programData = await channelService.getPrograms(
          null,
          startTimeDate,
          endTimeDate,
          settings.timezone,
        );
        setPrograms(programData);
        setProgramsLoading(false);
      } catch (error) {
        setProgramsLoading(false);
        console.error("Failed to initialize app:", error);
        setSettings((prev) => ({
          ...defaultSettings,
          ...prev,
          timezone: getUserTimezone(),
        }));
        setSettingsOpen(true);
      }
    };

    initializeApp();
  }, [settings.guideStartHour, settings.guideEndHour, settings.timezone]);

  // Add system theme listener
  useEffect(() => {
    if (settings?.theme === "system") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const handleChange = () => {
        setSettings((prev) => ({ ...prev }));
      };

      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
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
          handleM3uProgress,
        );
        // Refresh channel list after M3U download
        await channelListRef.current?.refresh();
      }

      if (newSettings.epgUrl) {
        await channelService.refreshEPG(
          newSettings.epgUrl,
          newSettings.epgUpdateInterval,
          false,
          handleEpgProgress,
        );
      }

      setSettingsOpen(false);
    } catch (error) {
      console.error("Failed to save settings:", error);
    }
  };

  const handleChannelSelect = (channel: Channel) => {
    setSelectedChannel(channel);
  };

  const handleToggleFavorite = async (channel: Channel) => {
    await channelService.toggleFavorite(channel.channel_id);
  };

  const handleM3uProgress = (
    current: number,
    total: number | ProgressMessage,
  ) => {
    if (typeof total === "object" && total.type === "complete") {
      setM3uProgress(null);
    } else if (typeof total === "number") {
      setM3uProgress({
        current,
        total,
        message: undefined,
      });
    } else if (typeof total === "object") {
      setM3uProgress({
        current,
        total: total.current || 0,
        message: total.message,
      });
    }
  };

  const handleEpgProgress = (
    current: number,
    total: number | ProgressMessage,
  ) => {
    if (typeof total === "object" && total.type === "complete") {
      setEpgProgress(null);
    } else if (typeof total === "number") {
      setEpgProgress({
        current,
        total,
        message: undefined,
      });
    } else if (typeof total === "object") {
      setEpgProgress({
        current,
        total: total.current || 0,
        message: total.message,
      });
    }
  };

  // Update channel list toggle to preserve EPG state
  const handleChannelListToggle = () => {
    setChannelListOpen((prev) => !prev); // Simply toggle the channel list state
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Box
          sx={{
            display: "flex",
            height: "100dvh",
            width: "100vw",
            overflow: "hidden",
            position: "relative",
          }}
        >
          <Box
            sx={{
              position: "absolute",
              left: 0,
              top: 0,
              bottom: 0,
              width: isMobile ? "100%" : "auto",
              minWidth: isMobile ? "100%" : 300,
              maxWidth: channelListOpen 
                ? isMobile 
                  ? "100%" // Full width on mobile
                  : "80vw"  // Desktop max width
                : 0,
              transform: channelListOpen ? "none" : "translateX(-100%)",
              transition: theme.transitions.create(["transform", "max-width"], {
                easing: theme.transitions.easing.sharp,
                duration: theme.transitions.duration.enteringScreen,
              }),
              zIndex: 2,
            }}
          >
            <ChannelList
              ref={channelListRef}
              onChannelSelect={handleChannelSelect}
              onToggleFavorite={handleToggleFavorite}
              selectedChannel={selectedChannel}
              onOpenSettings={() => setSettingsOpen(true)}
              programs={programs}
              channelListOpen={channelListOpen}
              setChannelListOpen={setChannelListOpen}
              settings={settings}
              timezone={settings.timezone}
              isMobile={isMobile}
              programsLoading={programsLoading}
            />
          </Box>

          <Box
            sx={{
              position: "absolute",
              left: channelListOpen 
                ? isMobile 
                  ? "100vw"  // Push completely off screen on mobile when list open
                  : 300      // Desktop offset
                : 0,
              right: 0,
              top: 0,
              bottom: 0,
              transition: theme.transitions.create("left", {
                easing: theme.transitions.easing.sharp,
                duration: theme.transitions.duration.enteringScreen,
              }),
            }}
          >
            <IconButton
              onClick={handleChannelListToggle}
              sx={{
                position: "fixed",
                left: channelListOpen ? (isMobile ? "auto" : 300) : 0,
                right: channelListOpen && isMobile ? 8 : "auto",
                top: 8,
                zIndex: 3,
                bgcolor: "background.paper",
                borderRadius:
                  channelListOpen && isMobile ? "4px" : "0 4px 4px 0",
                transition: theme.transitions.create(["left", "right"], {
                  easing: theme.transitions.easing.sharp,
                  duration: theme.transitions.duration.enteringScreen,
                }),
                "&:hover": {
                  bgcolor: "action.hover",
                },
              }}
            >
              {channelListOpen ? <ChevronLeftIcon /> : <MenuIcon />}
            </IconButton>

            <Routes>
              <Route
                path="/"
                element={
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "center",
                      alignItems: "center",
                      height: "100%",
                    }}
                  >
                    <Typography variant="h6" color="text.secondary">
                      Select a channel to begin
                    </Typography>
                  </Box>
                }
              />
              <Route
                path="/channel/:channelId"
                element={
                  selectedChannel ? (
                    <VideoPlayer channel={selectedChannel} />
                  ) : (
                    <Navigate to="/" replace />
                  )
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Box>
        </Box>
        <SettingsModal
          open={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          settings={settings ?? defaultSettings}
          onSave={handleSaveSettings}
          onM3uProgress={handleM3uProgress}
          onEpgProgress={handleEpgProgress}
        />
        <LoadingPopup m3uProgress={m3uProgress} epgProgress={epgProgress} />
      </BrowserRouter>
    </ThemeProvider>
  );
}