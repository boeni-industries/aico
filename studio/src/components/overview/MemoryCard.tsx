import React from 'react';
import { Box, Typography, LinearProgress, Chip } from '@mui/material';
import { HardDrive as MemoryIcon, Database as StorageIcon, GitBranch as GraphIcon, Gauge as SpeedIcon } from 'lucide-react';

interface MemoryCardProps {
  workingMemoryItems: number;
  semanticVectors: number;
  knowledgeGraphNodes: number;
  knowledgeGraphEdges: number;
  retrievalQuality: number;
  onClick?: () => void;
}

export const MemoryCard: React.FC<MemoryCardProps> = ({
  workingMemoryItems,
  semanticVectors,
  knowledgeGraphNodes,
  knowledgeGraphEdges,
  retrievalQuality,
  onClick,
}) => {
  return (
    <Box
      onClick={onClick}
      sx={{
        p: 3,
        borderRadius: '20px',
        border: '1.5px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
        cursor: 'pointer',
        transition: 'all 0.2s ease-in-out',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: '0 12px 32px rgba(0,0,0,0.12)',
          borderColor: 'primary.main',
        },
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: '12px',
              bgcolor: 'rgba(139, 92, 246, 0.12)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <MemoryIcon sx={{ color: '#8B5CF6', fontSize: 24 }} />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.1rem' }}>
              Memory & AMS
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
              Multi-Tier Architecture
            </Typography>
          </Box>
        </Box>
        <Chip
          label="LIVE"
          size="small"
          sx={{
            bgcolor: 'rgba(16, 185, 129, 0.12)',
            color: '#10B981',
            border: '1px solid',
            borderColor: 'rgba(16, 185, 129, 0.3)',
            fontWeight: 700,
            fontSize: '0.7rem',
            height: 24,
          }}
        />
      </Box>

      {/* Retrieval Quality */}
      <Box
        sx={{
          p: 2,
          mb: 2.5,
          borderRadius: '12px',
          bgcolor: 'rgba(139, 92, 246, 0.08)',
          border: '1px solid',
          borderColor: 'rgba(139, 92, 246, 0.2)',
        }}
      >
        <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', mb: 0.5, display: 'block' }}>
          RETRIEVAL QUALITY
        </Typography>
        <Typography variant="body2" sx={{ fontWeight: 600, color: '#8B5CF6', fontSize: '0.9rem' }}>
          {retrievalQuality}%
        </Typography>
      </Box>

      {/* Metrics Grid */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: 2,
          mb: 2.5,
        }}
      >
        {/* Working Memory */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <SpeedIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Working Items
            </Typography>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: 'text.primary' }}>
            {workingMemoryItems.toLocaleString()}
          </Typography>
        </Box>

        {/* Semantic Vectors */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <StorageIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Vector Docs
            </Typography>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: 'text.primary' }}>
            {(semanticVectors / 1000).toFixed(1)}K
          </Typography>
        </Box>

        {/* Knowledge Graph Nodes */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <GraphIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Graph Nodes
            </Typography>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: 'text.primary' }}>
            {knowledgeGraphNodes}
          </Typography>
        </Box>

        {/* Knowledge Graph Edges */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <GraphIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Graph Edges
            </Typography>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: 'text.primary' }}>
            {knowledgeGraphEdges}
          </Typography>
        </Box>
      </Box>

      {/* Footer Stats */}
      <Box
        sx={{
          display: 'flex',
          gap: 2,
          pt: 2.5,
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <Box
            sx={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              bgcolor: '#8B5CF6',
              boxShadow: '0 0 8px #8B5CF640',
            }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
            Multi-tier storage
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <GraphIcon sx={{ fontSize: 14, color: '#10B981' }} />
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
            Graph-enhanced
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};
