import React from "react";
import { LinearProgress, Typography, Paper } from "@mui/material";

export interface DownloadProgressProps {
  type: "M3U" | "EPG";
  current: number;
  total: number;
}

export const DownloadProgress: React.FC<DownloadProgressProps> = ({
  type,
  current,
  total,
}) => {
  const progress = total > 0 ? (current / total) * 100 : 0;
  const currentMB = (current / 1024 / 1024).toFixed(2);
  const totalMB = total > 0 ? (total / 1024 / 1024).toFixed(2) : "??";

  return (
    <Paper
      sx={{
        p: 1,
        width: "300px",
        position: "fixed",
        bottom: type === "M3U" ? 16 : 80,
        right: 16,
        zIndex: 9999,
      }}
    >
      <Typography variant="body2" color="textSecondary">
        {type} Update: {currentMB}MB {total > 0 ? `/ ${totalMB}MB` : ""}
      </Typography>
      <LinearProgress
        variant={total > 0 ? "determinate" : "indeterminate"}
        value={progress}
        sx={{ mt: 1 }}
      />
    </Paper>
  );
};

export {};
