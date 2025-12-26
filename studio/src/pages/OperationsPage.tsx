import React from 'react';
import { Box, Paper, Typography } from '@mui/material';

export const OperationsPage: React.FC = () => (
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
    <Typography variant="h1" sx={{ fontSize: '1.4rem', fontWeight: 600 }}>
      Operations
    </Typography>
    <Paper sx={{ p: 3 }}>
      <Typography variant="body1" color="text.secondary">
        Operations will surface runtime health, logs, scheduler state, and service
        metrics. This is a stub page.
      </Typography>
    </Paper>
  </Box>
);
