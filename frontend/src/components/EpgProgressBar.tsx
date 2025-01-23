import { Box, Typography, LinearProgress } from '@mui/material';

interface ProgressData {
  current: number;
  total: number;
  message?: string;
}

export const ProgressBar = ({ progress }: { progress: ProgressData | null }) => {
  if (!progress) return null;

  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: 16,
        right: 16,
        bgcolor: 'background.paper',
        borderRadius: 1,
        p: 2,
        boxShadow: 3,
        width: 300, // Fixed width for the container
      }}
    >
      <Typography variant="body2" sx={{ mb: 1 }}>
        {progress.message || `EPG: ${Math.round((progress.current / progress.total) * 100)}%`}
      </Typography>
      <LinearProgress
        variant="determinate"
        value={(progress.current / progress.total) * 100}
        sx={{
          height: 8, // Makes the progress bar a bit thicker
          borderRadius: 4, // Rounded corners for the progress bar
        }}
      />
    </Box>
  );
};