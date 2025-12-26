import React from 'react';
import { Box, Paper, Typography } from '@mui/material';

export const IntelligencePage: React.FC = () => (
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
    <Typography variant="h1" sx={{ fontSize: '1.4rem', fontWeight: 600 }}>
      Intelligence
    </Typography>
    <Paper sx={{ p: 3 }}>
      <Typography variant="body1" color="text.secondary">
        Intelligence will aggregate high-level AI insights, models, and sentiment
        analysis. This is a stub page.
      </Typography>
    </Paper>
  </Box>
);
