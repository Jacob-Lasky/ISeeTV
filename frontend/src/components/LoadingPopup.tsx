import { Dialog, DialogContent, CircularProgress, Typography, Box } from '@mui/material';

interface ProgressData {
  current: number;
  total: number;
  message?: string;
}

interface LoadingPopupProps {
  m3uProgress: ProgressData | null;
}

export const LoadingPopup = ({ m3uProgress }: LoadingPopupProps) => {
  return (
    <Dialog open={m3uProgress !== null} maxWidth="xs" fullWidth>
      <DialogContent>
        <Box sx={{ textAlign: 'center', py: 2 }}>
          {m3uProgress && (
            <Box>
              <Typography variant="body1" gutterBottom>
                {m3uProgress.message || `Updating M3U: ${Math.round((m3uProgress.current / m3uProgress.total) * 100)}%`}
              </Typography>
              <CircularProgress variant="determinate" value={(m3uProgress.current / m3uProgress.total) * 100} />
            </Box>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  );
}; 