import React, {
  useState,
  useCallback,
  useEffect,
  useRef,
  forwardRef,
  useImperativeHandle,
  useMemo,
} from "react";
import {
  Box,
  Paper,
  Avatar,
  TextField,
  IconButton,
  InputAdornment,
  CircularProgress,
  Typography,
  Tabs,
  Tab,
  Card,
  CardContent,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
} from "@mui/material";
import {
  Search as SearchIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Settings as SettingsIcon,
  ChevronRight,
  ChevronLeft,
  Close as CloseIcon,
} from "@mui/icons-material";
import { Channel } from "../models/Channel";
import { channelService } from "../services/channelService";
import { useNavigate } from "react-router-dom";
import { format } from "date-fns";
import { toZonedTime } from "date-fns-tz";
import {
  Epg,
  Layout,
  useEpg,
  useProgram,
  ProgramBox,
  ProgramContent,
  ProgramFlex,
  ProgramStack,
  ProgramTitle,
  ProgramText,
  ChannelBox,
} from "planby";
import { useTheme } from "@mui/material/styles";
import { formatTimeWithTimezone, getTodayOffsetDate } from "../utils/dateUtils";
import { Settings } from "../models/Settings";

const TIME_BLOCK_WIDTH = 150;
const HEADER_HEIGHT = 48;
const HOUR_WIDTH = TIME_BLOCK_WIDTH * 2;
const SCROLLBAR_WIDTH = 20; // Standard scrollbar width

// Add type for tab values
type TabValue = "all" | "favorites" | "recent";

// Add interface for program data
interface Program {
  id: string;
  title: string;
  start: Date;
  end: Date;
  duration: number;
  description: string;
  category: string;
}

// match Planby's expected format
interface PlanbyProgram {
  id: string;
  title: string;
  channelUuid: string;
  image: string;
  since: string; // ISO string
  till: string; // ISO string
  description: string;
  category: string;
  isLive?: boolean;
  position?: {
    // optional position data
    top: number;
    height: number;
    width: number;
    left: number;
  };
}

interface PlanbyChannel {
  uuid: string; // unique identifier
  logo: string; // required by Planby
  name: string;
  position?: {
    // optional position data
    top: number;
    height: number;
  };
}

interface ChannelListProps {
  selectedChannel?: Channel;
  onChannelSelect: (channel: Channel) => void;
  onToggleFavorite: (channel: Channel) => void;
  onRefresh?: (refreshFn: (() => Promise<void>) | undefined) => void;
  onOpenSettings?: () => void;
  onChannelsChange?: (channels: Channel[]) => void;
  programs?: Record<string, Program[]>;
  channelListOpen: boolean;
  timezone?: string;
  settings?: Settings;
  isMobile?: boolean;
  setChannelListOpen?: (open: boolean) => void;
  programsLoading?: boolean;
}

interface ProgramDialogProps {
  program: PlanbyProgram | null;
  onClose: () => void;
  onWatch: (channelId: string) => void;
  settings?: Settings;
}

interface ChannelDialogProps {
  channel: PlanbyChannel | null;
  onClose: () => void;
  onWatch: (channelId: string) => void;
  onToggleFavorite: (channelId: string) => void;
  isFavorite: boolean;
}

interface ProgramItemProps {
  program: {
    data: PlanbyProgram;
    styles: {
      width: number;
      position: React.CSSProperties;
    };
  };
  isBaseTimeFormat?: boolean;
  isMobile?: boolean;
  isLine?: boolean;
  // Add other known props as needed
}

interface ChannelItemProps {
  channel: PlanbyChannel;
}

// Add this near the top of the file, outside the component
const SEARCH_DELAY = 2000; // 2 seconds delay for single character

const ProgramDialog = ({
  program,
  onClose,
  onWatch,
  settings,
}: ProgramDialogProps) => {
  if (!program) return null;

  const timeFormat = settings?.use24Hour ? "HH:mm" : "h:mm a";

  return (
    <Dialog
      open={!!program}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: "100%",
          maxWidth: 400, // Match ChannelDialog width
          minHeight: 200, // Match ChannelDialog height
        },
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>{program.title}</DialogTitle>
      <DialogContent sx={{ pt: "8px !important" }}>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 1,
            mb: 2,
            minHeight: 56,
          }}
        >
          <Typography variant="subtitle1">
            {format(new Date(program.since), timeFormat)} -{" "}
            {format(new Date(program.till), timeFormat)}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Channel ID: {program.channelUuid}
          </Typography>
          {program.category && (
            <Typography variant="subtitle2" color="text.secondary">
              {program.category}
            </Typography>
          )}
          <Typography variant="body2" sx={{ mt: 1 }}>
            {program.description}
          </Typography>
        </Box>
      </DialogContent>
      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose}>Close</Button>
        <Button
          onClick={() => onWatch(program.channelUuid)}
          variant="contained"
        >
          Watch
        </Button>
      </DialogActions>
    </Dialog>
  );
};

const ChannelDialog = ({
  channel,
  onClose,
  onWatch,
  onToggleFavorite,
  isFavorite: initialIsFavorite,
}: ChannelDialogProps) => {
  const [isFavorite, setIsFavorite] = useState(initialIsFavorite);

  if (!channel) return null;

  const handleFavorite = () => {
    setIsFavorite(!isFavorite);
    onToggleFavorite(channel.uuid);
  };

  return (
    <Dialog
      open={!!channel}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: "100%",
          maxWidth: 400, // Set consistent max width
          minHeight: 200, // Set minimum height
        },
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>{channel.name}</DialogTitle>
      <DialogContent sx={{ pt: "8px !important" }}>
        <Box
          sx={{
            display: "flex",
            gap: 2,
            alignItems: "center",
            mb: 2,
            minHeight: 56, // Ensure consistent height for avatar section
          }}
        >
          <Avatar
            src={channel.logo}
            alt={channel.name}
            variant="square"
            sx={{ width: 48, height: 48 }} // Set consistent avatar size
          />
          <IconButton onClick={handleFavorite}>
            {isFavorite ? <StarIcon color="primary" /> : <StarBorderIcon />}
          </IconButton>
        </Box>
        <Typography variant="caption" color="text.secondary">
          Channel ID: {channel.uuid}
        </Typography>
      </DialogContent>
      <DialogActions sx={{ p: 2 }}>
        {" "}
        {/* Add consistent padding */}
        <Button onClick={onClose}>Close</Button>
        <Button onClick={() => onWatch(channel.uuid)} variant="contained">
          Watch
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export const ChannelList = forwardRef<
  { refresh: () => Promise<void> },
  ChannelListProps
>(
  (
    {
      onChannelSelect,
      onToggleFavorite,
      onRefresh,
      onOpenSettings,
      programs = {},
      channelListOpen,
      timezone = Intl.DateTimeFormat().resolvedOptions().timeZone,
      settings,
      isMobile,
      setChannelListOpen,
      programsLoading,
    },
    ref,
  ) => {
    // Update headerStyles
    const headerStyles = {
      container: {
        width: isMobile ? "100%" : 300,
        flexShrink: 0,
        zIndex: 3,
        bgcolor: "background.paper",
        borderBottom: 1,
        borderColor: "divider",
        display: "flex",
        flexDirection: "column",
      },
      groupSection: {
        width: isMobile ? "100%" : 300,
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        position: "relative",
        "&::before": {
          content: '""',
          position: "absolute",
          left: 0,
          top: 0,
          width: 4,
          height: "100%",
          bgcolor: "primary.main",
          opacity: 0.7,
        },
      },
      text: {
        color: "text.primary",
        fontWeight: 500,
        pl: 3,
        textTransform: "uppercase",
        letterSpacing: "0.5px",
        fontSize: "0.8125rem",
      },
    };

    const [activeTab, setActiveTab] = useState<TabValue>("all");
    const [searchTerm, setSearchTerm] = useState("");
    const [loading, setLoading] = useState(true);
    const [channels, setChannels] = useState<Channel[]>([]);
    const containerRef = useRef<HTMLDivElement>(null);
    const navigate = useNavigate();
    const [epgExpanded, setEpgExpanded] = useState(false);
    const theme = useTheme();
    const [selectedProgram, setSelectedProgram] =
      useState<PlanbyProgram | null>(null);
    const [selectedChannelDialog, setSelectedChannelDialog] =
      useState<PlanbyChannel | null>(null);
    const searchTimeoutRef = useRef<Window["setTimeout"]>();

    // Move planbyTheme inside the component to access theme
    const planbyTheme = useMemo(
      () => ({
        primary: {
          600: theme.palette.mode === "dark" ? "#040d1e" : "#b2eff7", // finished and upcoming programs
          900: theme.palette.mode === "dark" ? "#1f1f1f" : "#ffffff", // guide background
        },
        grey: {
          300: theme.palette.mode === "dark" ? "#d1d1d1" : "#757575",
        },
        white: theme.palette.mode === "dark" ? "#fff" : "#000",
        green: {
          300: theme.palette.primary.main, // Use MUI primary color
        },
        loader: {
          teal: theme.palette.primary.light,
          purple: theme.palette.primary.main,
          pink: theme.palette.primary.dark,
          bg: theme.palette.mode === "dark" ? "#171923db" : "#f5f5f5db",
        },
        scrollbar: {
          border: theme.palette.divider,
          thumb: {
            bg: theme.palette.mode === "dark" ? "#e1e1e1" : "#757575",
          },
        },
        // live channel gradient
        gradient: {
          blue: {
            300: theme.palette.mode === "dark" ? "#040d1e" : "#b2eff7",
            600: theme.palette.mode === "dark" ? "#001d31" : "#ceecf0",
            900: theme.palette.mode === "dark" ? "#040d1e" : "#b2eff7",
          },
        },
        text: {
          grey: {
            300: theme.palette.text.primary,
            500: theme.palette.text.secondary,
          },
        },
        timeline: {
          divider: {
            bg: theme.palette.divider,
          },
        },
      }),
      [theme],
    );

    // Modify loadChannels to not clear channels immediately
    const loadChannels = useCallback(async () => {
      try {
        // Don't set loading if we already have channels (prevents flash)
        if (channels.length === 0) {
          setLoading(true);
        }

        const response = await channelService.getChannels(0, {
          search: searchTerm,
          favoritesOnly: activeTab === "favorites",
          recentOnly: activeTab === "recent",
        });

        setChannels(response.items);
      } catch (error) {
        console.error("Failed to load channels:", error);
      } finally {
        setLoading(false);
      }
    }, [searchTerm, activeTab, channels.length]);

    // Update the effect to load channels on mount and when dependencies change
    useEffect(() => {
      loadChannels();
    }, [searchTerm, activeTab, loadChannels]);

    // Update handleSearch to not clear channels immediately
    const handleSearch = useCallback((term: string) => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }

      if (term.length === 1) {
        searchTimeoutRef.current = setTimeout(() => {
          setSearchTerm(term);
        }, SEARCH_DELAY);
      } else {
        setSearchTerm(term);
      }

      // Only set loading, don't clear channels
      setLoading(true);
      if (containerRef.current) {
        containerRef.current.scrollTop = 0;
      }
    }, []);

    // Clean up timeout on unmount
    useEffect(() => {
      return () => {
        if (searchTimeoutRef.current) {
          clearTimeout(searchTimeoutRef.current);
        }
      };
    }, []);

    // Add tab change handler
    const handleTabChange = useCallback(
      (_: React.SyntheticEvent, newValue: TabValue) => {
        setActiveTab(newValue);
        setChannels([]);
        if (containerRef.current) {
          containerRef.current.scrollTop = 0;
        }
      },
      [],
    );

    // Keep the refresh function for parent component
    const refresh = useCallback(async () => {
      setLoading(true);
      setChannels([]);
      await loadChannels();
    }, [loadChannels]);

    useImperativeHandle(
      ref,
      () => ({
        refresh,
      }),
      [refresh],
    );

    useEffect(() => {
      if (onRefresh) {
        onRefresh(refresh);
      }
    }, [onRefresh, refresh]);
    // Convert channels to Planby format
    const planbyChannels = useMemo<PlanbyChannel[]>(
      () =>
        channels.map((channel, index) => ({
          uuid: channel.channel_id,
          name: channel.name,
          logo:
            channel.logo || "/src/assets/logos/ISeeTV_Square_Blank_50pct.png", // Provide default logo
          position: {
            top: index * 70, // matches itemHeight in useEpg config
            height: 70,
          },
        })),
      [channels],
    );

    // Update the planbyPrograms memo to handle loading state
    const planbyPrograms = useMemo<PlanbyProgram[]>(() => {
      const allPrograms: PlanbyProgram[] = [];
      const now = new Date();
      const startTime = getTodayOffsetDate(settings?.guideStartHour ?? -1);

      try {
        Object.entries(programs).forEach(([channelId, channelPrograms]) => {
          const channel = channels.find((c) => c.channel_id === channelId);
          if (!channel) return;

          channelPrograms.forEach((program) => {
            const startDate = toZonedTime(new Date(program.start), timezone);
            const endDate = toZonedTime(new Date(program.end), timezone);

            // Calculate position data
            const durationMs = endDate.getTime() - startDate.getTime();
            const durationMinutes = durationMs / (1000 * 60);
            const width = (durationMinutes / 30) * TIME_BLOCK_WIDTH;
            const left =
              ((startDate.getTime() - startTime.getTime()) / (1000 * 60 * 30)) *
              TIME_BLOCK_WIDTH;

            allPrograms.push({
              id: program.id,
              title: program.title,
              since: startDate.toISOString(),
              till: endDate.toISOString(),
              channelUuid: channelId,
              image:
                theme.palette.mode === "dark"
                  ? "https://placehold.co/120x120/transparent/ffffff?font=noto-sans&text=ISeeTV"
                  : "https://placehold.co/120x120/transparent/121212?font=noto-sans&text=ISeeTV",
              description: program.description || "No description available",
              category: channel.group || program.category || "Uncategorized",
              isLive: startDate <= now && endDate >= now,
              position: {
                top: channels.findIndex((c) => c.channel_id === channelId) * 70,
                height: 70,
                width,
                left,
              },
            });
          });
        });
        return allPrograms;
      } finally {
      }
    }, [
      programs,
      channels,
      timezone,
      settings?.guideStartHour,
      theme.palette.mode,
    ]);

    const guideStartHour = settings?.guideStartHour ?? -1; // Default 2 hours back
    const guideEndHour = settings?.guideEndHour ?? 12; // Default 12 hours forward
    const guideStartDate = getTodayOffsetDate(guideStartHour);
    const guideEndDate = getTodayOffsetDate(guideEndHour);
    const formattedStartDate = format(guideStartDate, "yyyy-MM-dd'T'HH:mm:ss");
    const formattedEndDate = format(guideEndDate, "yyyy-MM-dd'T'HH:mm:ss");

    // Add height state
    const [containerHeight, setContainerHeight] = useState(
      window.innerHeight - HEADER_HEIGHT,
    );

    // Update the height observer effect
    useEffect(() => {
      const updateHeight = () => {
        if (containerRef.current) {
          const viewportHeight = window.innerHeight;
          const containerTop = containerRef.current.getBoundingClientRect().top;
          const newHeight = viewportHeight - containerTop;
          setContainerHeight(newHeight);
        }
      };

      // Initial height calculation
      updateHeight();

      // Update height on resize
      window.addEventListener("resize", updateHeight);

      // Create resize observer for parent element changes
      const resizeObserver = new ResizeObserver(updateHeight);
      if (containerRef.current?.parentElement) {
        resizeObserver.observe(containerRef.current.parentElement);
      }

      return () => {
        window.removeEventListener("resize", updateHeight);
        resizeObserver.disconnect();
      };
    }, []);

    // Add a constant for expanded width percentage
    const EXPANDED_WIDTH_PERCENTAGE = 80; // 80% of viewport width

    // First, declare the width state
    const [epgWidth, setEpgWidth] = useState(() =>
      channelListOpen
        ? epgExpanded
          ? isMobile
            ? window.innerWidth // Full width on mobile
            : Math.min(
                window.innerWidth * (EXPANDED_WIDTH_PERCENTAGE / 100),
                1200,
              )
          : 300
        : 0,
    );

    // Then use it in the EPG configuration
    const { getEpgProps, getLayoutProps } = useEpg({
      channels: planbyChannels,
      epg: planbyPrograms,
      width: epgWidth,
      height: containerHeight,
      itemHeight: 80,
      // Adjust sidebar width when expanded on mobile
      sidebarWidth:
        isMobile && epgExpanded
          ? window.innerWidth * 0.25 // 1/4 of screen width when expanded
          : isMobile
            ? window.innerWidth
            : 300,
      theme: planbyTheme,
      isBaseTimeFormat: !settings?.use24Hour,
      isSidebar: true,
      isTimeline: true,
      dayWidth: 24 * HOUR_WIDTH,
      isLine: epgExpanded,
      startDate: formattedStartDate,
      endDate: formattedEndDate,
    });

    // Keep the resize effects after
    useEffect(() => {
      const updateWidth = () => {
        setEpgWidth(
          channelListOpen
            ? epgExpanded
              ? isMobile
                ? window.innerWidth // Full width on mobile
                : Math.min(
                    window.innerWidth * (EXPANDED_WIDTH_PERCENTAGE / 100),
                    1200,
                  )
              : 300 + SCROLLBAR_WIDTH
            : 0,
        );
      };

      window.addEventListener("resize", updateWidth);
      return () => window.removeEventListener("resize", updateWidth);
    }, [channelListOpen, epgExpanded, isMobile]);

    useEffect(() => {
      setEpgWidth(
        channelListOpen
          ? epgExpanded
            ? isMobile
              ? window.innerWidth // Full width on mobile
              : Math.min(
                  window.innerWidth * (EXPANDED_WIDTH_PERCENTAGE / 100),
                  1200,
                )
            : 300 + SCROLLBAR_WIDTH
          : 0,
      );
    }, [channelListOpen, epgExpanded, isMobile]);

    // Custom Program component using Material-UI
    const ProgramItem = ({ program, ...rest }: ProgramItemProps) => {
      const { styles, isLive } = useProgram({ program, ...rest });

      const { data } = program;
      const { title, since, till } = data;

      const sinceTime = formatTimeWithTimezone(
        new Date(since),
        timezone,
        settings?.use24Hour ? "HH:mm" : "h:mm a",
      );
      const tillTime = formatTimeWithTimezone(
        new Date(till),
        timezone,
        settings?.use24Hour ? "HH:mm" : "h:mm a",
      );
      return (
        <ProgramBox
          width={styles.width}
          style={styles.position}
          onClick={() => setSelectedProgram(data)}
        >
          <ProgramContent width={styles.width} isLive={isLive}>
            <ProgramFlex>
              <ProgramStack>
                <ProgramTitle>{title}</ProgramTitle>
                <ProgramText>
                  {sinceTime} - {tillTime}
                </ProgramText>
              </ProgramStack>
            </ProgramFlex>
          </ProgramContent>
        </ProgramBox>
      );
    };

    // Custom Channel component using Material-UI
    const ChannelItem = ({ channel }: ChannelItemProps) => {
      const { position, logo, name } = channel;

      const handleClearLastWatched = async (e: React.MouseEvent) => {
        e.stopPropagation(); // Prevent channel dialog from opening
        try {
          await channelService.clearLastWatched(channel.uuid);
          // Refresh the channel list to update the UI
          await loadChannels();
        } catch (error) {
          console.error("Failed to clear last watched:", error);
        }
      };

      return (
        <ChannelBox {...position}>
          <Card
            sx={{
              height: "100%",
              width: "100%",
              display: "flex",
              alignItems: "center",
              borderRadius: 0,
              bgcolor: "background.paper",
              cursor: "pointer",
              transition: "background-color 0.2s",
              "&:hover": {
                bgcolor: "action.hover",
              },
            }}
            onClick={() => setSelectedChannelDialog(channel)}
          >
            <CardContent
              sx={{
                p: 1,
                "&:last-child": { pb: 1 },
                display: "flex",
                alignItems: "flex-start",
                gap: 1,
                width: "100%",
                position: "relative", // Add this for absolute positioning of X button
              }}
            >
              <Avatar
                src={logo}
                alt={name}
                variant="square"
                sx={{
                  width: 32,
                  height: 32,
                  flexShrink: 0,
                }}
              />
              <Typography
                sx={{
                  wordBreak: "break-word",
                  whiteSpace: "normal",
                  overflow: "hidden",
                  fontSize: "0.875rem",
                  lineHeight: 1.2,
                  maxHeight: "2.4em",
                  WebkitLineClamp: 2,
                  display: "-webkit-box",
                  WebkitBoxOrient: "vertical",
                }}
              >
                {name}
              </Typography>
              {/* Add X button only in recent tab */}
              {activeTab === "recent" && (
                <IconButton
                  size="small"
                  onClick={handleClearLastWatched}
                  sx={{
                    position: "absolute",
                    right: 8,
                    top: "50%",
                    transform: "translateY(-50%)",
                    opacity: 0.7,
                    "&:hover": {
                      opacity: 1,
                    },
                  }}
                >
                  <CloseIcon fontSize="small" />
                </IconButton>
              )}
            </CardContent>
          </Card>
        </ChannelBox>
      );
    };

    return (
      <Paper
        elevation={3}
        sx={{ height: "100%", display: "flex", flexDirection: "column" }}
      >
        {/* Fixed width header section */}
        <Box sx={headerStyles.container}>
          {/* Search Bar */}
          <Box
            sx={{
              p: 1,
              display: "flex",
              alignItems: "center",
              gap: 1,
              // Add margin-right when mobile and channel list is open
              mr: isMobile && channelListOpen ? 5 : 0, // Add space for collapse button
            }}
          >
            <TextField
              fullWidth
              size="small"
              placeholder="Search channels..."
              onChange={(e) => handleSearch(e.target.value)}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                },
              }}
            />
            {onOpenSettings && (
              <IconButton onClick={onOpenSettings} size="small">
                <SettingsIcon />
              </IconButton>
            )}
          </Box>

          {/* Tabs and EPG Toggle */}
          <Box sx={{ display: "flex", alignItems: "center" }}>
            <Tabs
              value={activeTab}
              onChange={handleTabChange}
              variant="fullWidth"
              sx={{ flexGrow: 1 }}
            >
              <Tab label="All" value="all" />
              <Tab label="Favorites" value="favorites" />
              <Tab label="Recent" value="recent" />
            </Tabs>
            <IconButton
              onClick={() => setEpgExpanded(!epgExpanded)}
              sx={{
                borderRadius: "4px 0 0 4px",
                bgcolor: "background.paper",
                "&:hover": { bgcolor: "action.hover" },
              }}
            >
              {epgExpanded ? <ChevronLeft /> : <ChevronRight />}
            </IconButton>
          </Box>
        </Box>

        {/* Update EPG section */}
        <Box
          ref={containerRef}
          sx={{
            flexGrow: 1,
            overflow: "hidden",
            bgcolor: "background.default",
            position: "relative",
            display: "flex",
            flexDirection: "column",
            height: containerHeight,
          }}
        >
          {/* Add overlay text */}
          <Box
            sx={{
              position: "absolute",
              top: 0,
              left: 0,
              height: 60,
              zIndex: 1000,
              display: "flex",
              alignItems: "center",
              px: 2,
              color: "text.primary",
              pointerEvents: "none",
              // Hide when guide is expanded on mobile
              opacity: isMobile && epgExpanded ? 0 : 1,
              visibility: isMobile && epgExpanded ? "hidden" : "visible",
            }}
          >
            <Stack>
              <Typography>{channels.length} Channels</Typography>
              <Typography>{planbyPrograms.length} Programs</Typography>
            </Stack>
          </Box>
          <Epg {...getEpgProps()}>
            <Layout
              {...getLayoutProps()}
              renderProgram={({ program, ...rest }) => (
                <ProgramItem
                  key={program.data.id}
                  program={program}
                  {...rest}
                />
              )}
              renderChannel={({ channel }) => (
                <ChannelItem key={channel.uuid} channel={channel} />
              )}
            />
          </Epg>
        </Box>

        {/* Update the loading state display */}
        {(loading || programsLoading) && (
          <Box
            sx={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              bgcolor: "rgba(0, 0, 0, 0.3)",
              zIndex: 1001,
            }}
          >
            <CircularProgress />
          </Box>
        )}

        <ProgramDialog
          program={selectedProgram}
          onClose={() => setSelectedProgram(null)}
          onWatch={(channelId) => {
            onChannelSelect(channels.find((c) => c.channel_id === channelId)!);
            setSelectedProgram(null);
            navigate(`/channel/${channelId}`);
            if (isMobile && setChannelListOpen) {
              setChannelListOpen(false);
            }
          }}
          settings={settings}
        />

        <ChannelDialog
          channel={selectedChannelDialog}
          onClose={() => setSelectedChannelDialog(null)}
          onWatch={(channelId) => {
            onChannelSelect(channels.find((c) => c.channel_id === channelId)!);
            setSelectedChannelDialog(null);
            navigate(`/channel/${channelId}`);
            if (isMobile && setChannelListOpen) {
              setChannelListOpen(false);
            }
          }}
          onToggleFavorite={(channelId) => {
            const channel = channels.find((c) => c.channel_id === channelId);
            if (channel) {
              onToggleFavorite(channel);
            }
          }}
          isFavorite={
            channels.find((c) => c.channel_id === selectedChannelDialog?.uuid)
              ?.isFavorite || false
          }
        />
      </Paper>
    );
  },
);

ChannelList.displayName = "ChannelList";

export type { ChannelListProps };
