import React from 'react';
import { Box, Paper, Typography } from '@mui/material';

export const MemoryAmsPage: React.FC = () => (
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
    <Typography variant="h1" sx={{ fontSize: '1.4rem', fontWeight: 600 }}>
      Memory & AMS
    </Typography>
    <Paper sx={{ p: 3 }}>
      <Typography variant="body1" color="text.secondary">
        Memory & AMS will expose working memory, semantic memory, knowledge graph,
        and consolidation status. This is a stub page.
      </Typography>
    </Paper>
  </Box>
);
