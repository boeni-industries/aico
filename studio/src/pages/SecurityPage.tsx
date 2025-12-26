import React from 'react';
import { Box, Paper, Typography } from '@mui/material';

export const SecurityPage: React.FC = () => (
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
    <Typography variant="h1" sx={{ fontSize: '1.4rem', fontWeight: 600 }}>
      Security
    </Typography>
    <Paper sx={{ p: 3 }}>
      <Typography variant="body1" color="text.secondary">
        Security will surface keys, sessions, audit logs, and transport encryption
        state. This is a stub page.
      </Typography>
    </Paper>
  </Box>
);
