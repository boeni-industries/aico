import React from 'react';
import { Box, Paper, Typography } from '@mui/material';

export const OverviewPage: React.FC = () => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Typography variant="h1" sx={{ fontSize: '1.6rem', fontWeight: 700 }}>
        Studio Overview
      </Typography>
      <Paper sx={{ p: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Welcome to AICO Studio
        </Typography>
        <Typography variant="body1" color="text.secondary">
          This is the unified admin and observability dashboard. From here you will
          navigate Operations, Intelligence, Memory & AMS, Agency, Security, and System
          domains once the modules are wired in.
        </Typography>
      </Paper>
    </Box>
  );
};
