import React from 'react';
import { Box, Paper, Typography } from '@mui/material';

export const SystemPage: React.FC = () => (
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
    <Typography variant="h1" sx={{ fontSize: '1.4rem', fontWeight: 600 }}>
      System
    </Typography>
    <Paper sx={{ p: 3 }}>
      <Typography variant="body1" color="text.secondary">
        System will host updates, configuration, plugins, and developer tools. This is
        a stub page.
      </Typography>
    </Paper>
  </Box>
);
