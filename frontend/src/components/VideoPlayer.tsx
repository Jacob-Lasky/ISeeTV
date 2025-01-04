import React, { useState, useCallback, useEffect } from 'react';
import { Box, Paper, Avatar, Typography, IconButton } from '@mui/material';
import Hls from 'hls.js';
import { Channel } from '../models/Channel';
import { API_URL } from '../config/api';
import { useParams, useNavigate } from 'react-router-dom';
import { Close } from '@mui/icons-material';

export {};

interface VideoPlayerProps {
  url: string;
  channel: Channel;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({ url, channel }) => {
  const { channelId } = useParams();
  const navigate = useNavigate();
  const videoRef = React.useRef<HTMLVideoElement>(null);
  const hlsRef = React.useRef<Hls | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);

  const cleanupStream = useCallback(async () => {
    try {
      await fetch(`${API_URL}/stream/${channel.guide_id}/cleanup`, {
        method: 'GET',
      });
    } catch (error) {
      console.error('Failed to cleanup stream:', error);
    }
  }, [channel.guide_id]);

  React.useEffect(() => {
    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }
      cleanupStream();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  React.useEffect(() => {
    if (!videoRef.current) return;

    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }

    const timeoutId = setTimeout(async () => {
      try {
        await cleanupStream();
        
        if (Hls.isSupported()) {
          const video = videoRef.current;
          if (!video) return;

          const proxyUrl = `${API_URL}/stream/${channel.guide_id}`;
          const hls = new Hls({
            maxBufferLength: Infinity,  // the maximum number of seconds to buffer
            maxMaxBufferLength: Infinity,  // allow up to 120 seconds
            manifestLoadingMaxRetry: 10,
            manifestLoadingRetryDelay: 500,  // retry every X milliseconds
            levelLoadingMaxRetry: 5,  // Retry level loading X times
            enableWorker: true,
            liveDurationInfinity: true,  // Indicates it's a live stream
          });

          hlsRef.current = hls;
          hls.loadSource(proxyUrl);
          hls.attachMedia(video);

          hls.on(Hls.Events.MANIFEST_PARSED, () => {
            video.play()
              .catch((e) => {
                console.warn('Autoplay prevented:', e);
                setIsPlaying(false);
              });
          });

          hls.on(Hls.Events.ERROR, (_, data) => {
            console.warn('HLS error:', data);
            if (data.fatal) {
              setIsPlaying(false);
              switch (data.type) {
                case Hls.ErrorTypes.NETWORK_ERROR:
                  console.warn('Network error, attempting recovery...');
                  hls.startLoad();
                  break;
                case Hls.ErrorTypes.MEDIA_ERROR:
                  console.warn('Media error, attempting recovery...');
                  hls.recoverMediaError();
                  break;
                default:
                  console.error('Fatal error:', data);
                  hls.destroy();
                  break;
              }
            }
          });
        }
      } catch (error) {
        console.error('Error switching channels:', error);
        setErrorMessage('Failed to switch channels');
        setIsPlaying(false);
      }
    }, 1000);

    return () => {
      clearTimeout(timeoutId);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channel.guide_id, cleanupStream]);

  const handleBack = () => {
    navigate('/');
  };

  useEffect(() => {
    if (channelId) {
      // Load channel data using channelId
    }
  }, [channelId]);

  return (
    <Paper elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 1, display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
        <IconButton onClick={handleBack}>
          <Close />
        </IconButton>
      </Box>
      <Box
        sx={{
          width: '100%',
          height: '100%',
          maxHeight: 'calc(100vh - 160px)',
          bgcolor: 'black',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {errorMessage && (
          <Typography variant="body1" color="error" sx={{ textAlign: 'center' }}>
            {errorMessage}
          </Typography>
        )}
        {isPlaying && (
          <video
            ref={videoRef}
            controls
            style={{
              width: '100%',
              height: '100%',
              maxHeight: '100%',
              objectFit: 'contain',
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
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          borderTop: 1,
          borderColor: 'divider',
        }}
      >
        {/* Left side with channel info */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexGrow: 1 }}>
          <Avatar
            src={channel.logo}
            alt={channel.name}
            variant="square"
            sx={{ width: 40, height: 40 }}
          >
            {channel.name[0]}
          </Avatar>
          <Typography variant="h6" component="div">
            {channel.name}
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
};
