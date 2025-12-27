import React from 'react';
import { Box, Typography, Paper, Chip } from '@mui/material';

interface SemanticMemoryPanelProps {
  vectorCount: number;
  indexSize: string;
  avgLatency: number;
  collections: Array<{
    name: string;
    count: number;
    dimension: number;
  }>;
}

export const SemanticMemoryPanel: React.FC<SemanticMemoryPanelProps> = ({
  vectorCount,
  indexSize,
  avgLatency,
  collections,
}) => {
  return (
    <Box>
      <Typography
        variant="subtitle2"
        sx={{
          fontWeight: 600,
          mb: 2,
          textTransform: 'uppercase',
          fontSize: '0.75rem',
          letterSpacing: '0.1em',
          color: 'text.secondary',
        }}
      >
        Semantic Memory (ChromaDB)
      </Typography>

      {/* Metrics Grid */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2, mb: 3 }}>
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(139, 92, 246, 0.08)', border: '1px solid rgba(139, 92, 246, 0.2)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 0.5, display: 'block' }}>
            VECTOR COUNT
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#8B5CF6' }}>
            {vectorCount.toLocaleString()}
          </Typography>
        </Paper>

        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 0.5, display: 'block' }}>
            INDEX SIZE
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#10B981' }}>
            {indexSize}
          </Typography>
        </Paper>

        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 0.5, display: 'block' }}>
            AVG LATENCY
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#3B82F6' }}>
            {avgLatency}ms
          </Typography>
        </Paper>
      </Box>

      {/* Collections */}
      <Box>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1.5, display: 'block' }}>
          COLLECTIONS
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {collections.map((collection) => (
            <Paper
              key={collection.name}
              sx={{
                p: 2,
                borderRadius: '12px',
                border: '1px solid',
                borderColor: 'divider',
                bgcolor: 'rgba(255, 255, 255, 0.02)',
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.85rem' }}>
                  {collection.name}
                </Typography>
                <Chip
                  label={`${collection.count.toLocaleString()} vectors`}
                  size="small"
                  sx={{
                    height: 20,
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    bgcolor: 'rgba(139, 92, 246, 0.12)',
                    color: '#8B5CF6',
                    border: '1px solid rgba(139, 92, 246, 0.3)',
                  }}
                />
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                Dimension: {collection.dimension}
              </Typography>
            </Paper>
          ))}
        </Box>
      </Box>
    </Box>
  );
};
