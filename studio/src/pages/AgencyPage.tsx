import React from 'react';
import { Box, Paper, Typography } from '@mui/material';

export const AgencyPage: React.FC = () => (
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
    <Typography variant="h1" sx={{ fontSize: '1.4rem', fontWeight: 600 }}>
      Agency
    </Typography>
    <Paper sx={{ p: 3 }}>
      <Typography variant="body1" color="text.secondary">
        Agency will show goals, plans, lessons, and initiative state for AICO&apos;s
        autonomous behavior. This is a stub page.
      </Typography>
    </Paper>
  </Box>
);
