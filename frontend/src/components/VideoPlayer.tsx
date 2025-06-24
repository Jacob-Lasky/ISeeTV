import React, { useState, useCallback, useEffect } from "react";
import { Box, Paper, Avatar, Typography, IconButton } from "@mui/material";
import { Channel } from "../models/Channel";
import { API_URL } from "../config/api";
import { useParams, useNavigate } from "react-router-dom";
import { Close } from "@mui/icons-material";

export {};

interface VideoPlayerProps {
  url: string;
  channel: Channel;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({ channel }) => {
  const { channelId } = useParams();
  const navigate = useNavigate();
  const videoRef = React.useRef<HTMLVideoElement>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);

  const cleanupStream = useCallback(async () => {
    try {
      await fetch(`${API_URL}/stream/${channel.channel_id}/cleanup`, {
        method: "GET",
      });
    } catch (error) {
      console.error("Failed to cleanup stream:", error);
    }
  }, [channel.channel_id]);

  React.useEffect(() => {
    return () => {
      cleanupStream();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  React.useEffect(() => {
    if (!videoRef.current) return;

    const timeoutId = setTimeout(async () => {
      try {
        await cleanupStream();

        const video = videoRef.current;
        if (!video) return;

        // Use the stream.ts file directly
        const streamUrl = `${API_URL}/stream/${channel.channel_id}`;
        
        // Set up video element for MPEG-TS streaming
        video.src = streamUrl;
        
        // Add event listeners for better error handling
        video.onloadeddata = () => {
          console.log("Video data loaded successfully");
          setIsPlaying(true);
        };
        
        video.onerror = (e) => {
          console.error("Video error:", e);
          setErrorMessage("Failed to play video");
          setIsPlaying(false);
        };
        
        // Try to play the video
        const playPromise = video.play();
        if (playPromise !== undefined) {
          playPromise.catch((e) => {
            console.warn("Autoplay prevented:", e);
            setIsPlaying(false);
          });
        }
      } catch (error) {
        console.error("Error switching channels:", error);
        setErrorMessage("Failed to switch channels");
        setIsPlaying(false);
      }
    }, 1000);

    return () => {
      clearTimeout(timeoutId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channel.channel_id, cleanupStream]);

  const handleBack = () => {
    navigate("/");
  };

  useEffect(() => {
    if (channelId) {
      // Load channel data using channelId
    }
  }, [channelId]);

  return (
    <Paper
      elevation={3}
      sx={{ height: "100%", display: "flex", flexDirection: "column" }}
    >
      <Box
        sx={{
          p: 1,
          display: "flex",
          justifyContent: "flex-end",
          alignItems: "center",
        }}
      >
        <IconButton onClick={handleBack}>
          <Close />
        </IconButton>
      </Box>
      <Box
        sx={{
          width: "100%",
          height: "100%",
          maxHeight: "calc(100vh - 160px)",
          bgcolor: "black",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {errorMessage && (
          <Typography
            variant="body1"
            color="error"
            sx={{ textAlign: "center" }}
          >
            {errorMessage}
          </Typography>
        )}
        {isPlaying && (
          <video
            ref={videoRef}
            controls
            style={{
              width: "100%",
              height: "100%",
              maxHeight: "100%",
              objectFit: "contain",
            }}
            playsInline
            autoPlay
          />
        )}
      </Box>

      {/* Channel Info Bar */}
      <Box
        sx={{
          p: 1,
          display: "flex",
          alignItems: "center",
          gap: 2,
          borderTop: 1,
          borderColor: "divider",
        }}
      >
        {/* Left side with channel info */}
        <Box
          sx={{ display: "flex", alignItems: "center", gap: 2, flexGrow: 1 }}
        >
          {channel.logo ? (
            <Avatar
              src={channel.logo}
              alt={channel.name}
              variant="square"
              sx={{ width: 40, height: 40 }}
            >
              {channel.name[0]}
            </Avatar>
          ) : (
            <Avatar
              alt={channel.name}
              variant="square"
              sx={{ width: 40, height: 40 }}
            >
              {channel.name[0]}
            </Avatar>
          )}
          <Typography variant="h6" component="div">
            {channel.name}
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
};
