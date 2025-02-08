import { Dialog, DialogContent, Typography, LinearProgress } from '@mui/material';

interface ProgressData {
  current: number;
  total: number;
  message?: string;
}

interface LoadingPopupProps {
  m3uProgress: ProgressData | null;
  epgProgress: ProgressData | null;
}

export const LoadingPopup = ({ m3uProgress, epgProgress }: LoadingPopupProps) => {
  const isLoading = m3uProgress !== null || epgProgress !== null;
  
  return (
    <Dialog open={isLoading} maxWidth="sm" fullWidth>
      <DialogContent>
        {m3uProgress && (
          <>
            <Typography>Loading M3U Playlist...</Typography>
            <LinearProgress 
              variant="determinate" 
              value={(m3uProgress.current / m3uProgress.total) * 100} 
            />
            {m3uProgress.message && (
              <Typography variant="caption" color="textSecondary">
                {m3uProgress.message}
              </Typography>
            )}
          </>
        )}
        {epgProgress && (
          <>
            <Typography>Loading EPG Data...</Typography>
            <LinearProgress 
              variant="determinate" 
              value={(epgProgress.current / epgProgress.total) * 100} 
            />
            {epgProgress.message && (
              <Typography variant="caption" color="textSecondary">
                {epgProgress.message}
              </Typography>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}; 