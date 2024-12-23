import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Box, Paper, Avatar, Typography } from '@mui/material';
import Hls from 'hls.js';
import { Channel } from '../models/Channel';
import { API_URL } from '../config/api';

interface VideoPlayerProps {
  url: string;
  channel: Channel;
  onError?: (error: string) => void;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({ url, channel, onError }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const retryCountRef = useRef(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);

  const cleanupStream = useCallback(async () => {
    try {
      // Only cleanup if we have an active stream
      if (hlsRef.current) {
        await fetch(`${API_URL}/stream/${channel.channel_number}/cleanup`, {
          method: 'GET',
        });
      }
    } catch (error) {
      console.error('Failed to cleanup stream:', error);
    }
  }, [channel.channel_number]);

  const initializeHls = useCallback(async () => {
    if (!videoRef.current) return;

    try {
      // Ensure cleanup of previous stream
      await cleanupStream();
      
      if (Hls.isSupported()) {
        const video = videoRef.current;
        if (!video) return;

        const proxyUrl = `${API_URL}/stream/${channel.channel_number}`;
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

        // Set up handlers before loading source
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          hls.startLoad(-1);  // Start loading from the beginning
          video.play().catch(console.error);
          retryCountRef.current = 0;
        });

        hls.on(Hls.Events.ERROR, (event, data) => {
          console.warn('HLS error:', data);
          if (data.fatal) {
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                console.warn('Network error, attempting recovery...');
                setTimeout(() => {
                  hls.startLoad();
                }, 2000);
                break;
              case Hls.ErrorTypes.MEDIA_ERROR:
                console.warn('Media error, attempting recovery...');
                setTimeout(() => {
                  hls.recoverMediaError();
                }, 2000);
                break;
              default:
                if (retryCountRef.current < 3) {
                  console.warn('Fatal error, attempting reinitialize...');
                  retryCountRef.current++;
                  setTimeout(() => {
                    hls.destroy();
                    initializeHls();
                  }, 2000);
                } else {
                  console.error('Fatal error after retries:', data);
                  setIsPlaying(false);
                  setErrorMessage('Failed to load stream after multiple attempts');
                }
                break;
            }
          } else if (data.details === Hls.ErrorDetails.BUFFER_STALLED_ERROR) {
            console.warn('Buffer stalled, reloading stream...');
            hls.stopLoad();
            setTimeout(() => {
              hls.startLoad();
              video.currentTime = video.duration - 0.5;
            }, 1000);
          }
        });

        // Load source after setting up handlers
        hls.loadSource(proxyUrl);
        hls.attachMedia(video);

        return () => {
          hls.destroy();
        };
      }
    } catch (error) {
      console.error('Error initializing HLS:', error);
      setErrorMessage('Failed to initialize stream');
      setIsPlaying(false);
      onError?.('Failed to initialize stream');
    }
  }, [channel.channel_number, cleanupStream, isPlaying, onError]);
  // Handle component mount/unmount
  useEffect(() => {
    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }
      cleanupStream();
    };
  }, [cleanupStream]);

  // Handle channel changes
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }
      initializeHls();
    }, 500); // Reduced from 1000ms

    return () => {
      clearTimeout(timeoutId);
    };
  }, [channel.channel_number, initializeHls]);

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
        {errorMessage ? (
          <Typography variant="body1" color="error" sx={{ textAlign: 'center' }}>
            {errorMessage}
          </Typography>
        ) : (
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

      <Box sx={{ p: 1, display: 'flex', alignItems: 'center', gap: 2, borderTop: 1, borderColor: 'divider' }}>
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