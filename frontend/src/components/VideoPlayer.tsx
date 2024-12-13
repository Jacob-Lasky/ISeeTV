import React from 'react';
import { Box, Paper, Avatar, Typography, IconButton } from '@mui/material';
import Hls from 'hls.js';
import { Channel } from '../models/Channel';
import { API_URL } from '../config/api';
import StopIcon from '@mui/icons-material/Stop';

export {};

interface VideoPlayerProps {
  url: string;
  channel: Channel;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({ url, channel }) => {
  const videoRef = React.useRef<HTMLVideoElement>(null);
  const hlsRef = React.useRef<Hls | null>(null);
  const abortControllerRef = React.useRef<AbortController | null>(null);

  const handleStopStream = () => {
    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.src = '';
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  React.useEffect(() => {
    if (!videoRef.current) return;

    const video = videoRef.current;
    const proxyUrl = `${API_URL}/stream/${channel.channel_number}`;
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    if (Hls.isSupported()) {
      if (hlsRef.current) {
        hlsRef.current.destroy();
      }

      const hls = new Hls({
        maxBufferLength: 60,  // the maximum number of seconds to buffer
        maxMaxBufferLength: 120,  // allow up to 120 seconds
        // liveSyncDurationCount: 10,  // buffer at least X segments
        // liveMaxLatencyDurationCount: 20,  // allow up to X segments of latency, must be greater than liveSyncDurationCount
        // maxBufferSize: 60 * 1000 * 1000,
        manifestLoadingMaxRetry: 10,
        manifestLoadingRetryDelay: 500,  // retry every X milliseconds
        levelLoadingMaxRetry: 5,  // Retry level loading X times
        enableWorker: true,
      });

      hlsRef.current = hls;

      hls.loadSource(proxyUrl);
      hls.attachMedia(video);

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch((e) => console.warn('Autoplay prevented:', e));
      });

      hls.on(Hls.Events.ERROR, (_, data) => {
        console.warn('HLS error:', data);
        if (data.fatal) {
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

      return () => {
        hls.destroy();
        video.pause();
        video.src = '';
        abortController.abort();
        hlsRef.current = null;
        abortControllerRef.current = null;
      };
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      // For Safari
      video.src = proxyUrl;
      video.play().catch((e) => console.warn('Autoplay prevented:', e));

      return () => {
        video.pause();
        video.src = '';
        abortController.abort();
        abortControllerRef.current = null;
      };
    }
  }, [channel.channel_number]);

  return (
    <Paper elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
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

        {/* Right side with stop button */}
        <IconButton onClick={handleStopStream} size="small" title="Stop Stream">
          <StopIcon />
        </IconButton>
      </Box>
    </Paper>
  );
};
