import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  LinearProgress,
  Typography,
  Box,
} from '@mui/material';

interface ProgressDialogProps {
  open: boolean;
  title: string;
  message: string;
  progress?: number;
}

export const ProgressDialog: React.FC<ProgressDialogProps> = ({
  open,
  title,
  message,
  progress,
}) => {
  return (
    <Dialog open={open} maxWidth="sm" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Box sx={{ width: '100%', mt: 1 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {message}
          </Typography>
          <LinearProgress 
            variant={progress !== undefined ? "determinate" : "indeterminate"} 
            value={progress} 
          />
        </Box>
      </DialogContent>
    </Dialog>
  );
}; 