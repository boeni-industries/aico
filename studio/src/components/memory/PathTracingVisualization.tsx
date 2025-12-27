import React from 'react';
import { Box, Typography, Paper, Chip } from '@mui/material';
import { ArrowForward as ArrowIcon } from '@mui/icons-material';

interface PathNode {
  id: string;
  label: string;
  type: string;
}

interface PathEdge {
  relation_type: string;
  confidence: number;
}

interface GraphPath {
  nodes: PathNode[];
  edges: PathEdge[];
  total_weight: number;
  hop_count: number;
}

interface PathTracingVisualizationProps {
  paths: GraphPath[];
  onNodeClick?: (nodeId: string) => void;
}

const nodeTypeColors: Record<string, string> = {
  person: '#8B5CF6',
  project: '#8B5CF6',
  goal: '#10B981',
  task: '#3B82F6',
  skill: '#EC4899',
  interest: '#EC4899',
  event: '#10B981',
};

export const PathTracingVisualization: React.FC<PathTracingVisualizationProps> = ({
  paths,
  onNodeClick,
}) => {
  if (!paths || paths.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center', borderRadius: '16px' }}>
        <Typography variant="body2" color="text.secondary">
          No paths found between selected nodes
        </Typography>
      </Paper>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Relationship Paths ({paths.length})
        </Typography>
        <Chip
          label={`Shortest: ${paths[0]?.hop_count || 0} hops`}
          sx={{
            bgcolor: 'rgba(16, 185, 129, 0.12)',
            color: '#10B981',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            fontWeight: 700,
          }}
        />
      </Box>

      {paths.map((path, pathIndex) => (
        <Paper
          key={pathIndex}
          sx={{
            p: 3,
            borderRadius: '16px',
            border: '1.5px solid',
            borderColor: pathIndex === 0 ? 'primary.main' : 'divider',
            bgcolor: pathIndex === 0 ? 'rgba(139, 92, 246, 0.04)' : 'background.paper',
          }}
        >
          {/* Path Header */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Box sx={{ display: 'flex', gap: 1.5 }}>
              <Chip
                label={`Path ${pathIndex + 1}`}
                size="small"
                sx={{
                  bgcolor: pathIndex === 0 ? 'rgba(139, 92, 246, 0.12)' : 'rgba(148, 163, 184, 0.12)',
                  color: pathIndex === 0 ? '#8B5CF6' : '#94A3B8',
                  fontWeight: 700,
                }}
              />
              <Chip
                label={`${path.hop_count} hops`}
                size="small"
                sx={{
                  bgcolor: 'rgba(59, 130, 246, 0.12)',
                  color: '#3B82F6',
                }}
              />
              <Chip
                label={`Weight: ${path.total_weight.toFixed(2)}`}
                size="small"
                sx={{
                  bgcolor: 'rgba(245, 158, 11, 0.12)',
                  color: '#F59E0B',
                }}
              />
            </Box>
          </Box>

          {/* Path Visualization */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
            {path.nodes.map((node, nodeIndex) => (
              <React.Fragment key={node.id}>
                {/* Node */}
                <Paper
                  onClick={() => onNodeClick?.(node.id)}
                  sx={{
                    p: 2,
                    minWidth: 140,
                    borderRadius: '12px',
                    border: '1.5px solid',
                    borderColor: nodeTypeColors[node.type.toLowerCase()] || '#94A3B8',
                    bgcolor: `${nodeTypeColors[node.type.toLowerCase()] || '#94A3B8'}10`,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: `0 4px 12px ${nodeTypeColors[node.type.toLowerCase()] || '#94A3B8'}40`,
                    },
                  }}
                >
                  <Chip
                    label={node.type.toUpperCase()}
                    size="small"
                    sx={{
                      height: 18,
                      fontSize: '0.6rem',
                      mb: 1,
                      bgcolor: `${nodeTypeColors[node.type.toLowerCase()] || '#94A3B8'}20`,
                      color: nodeTypeColors[node.type.toLowerCase()] || '#94A3B8',
                      fontWeight: 700,
                    }}
                  />
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 600,
                      fontSize: '0.85rem',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {node.label}
                  </Typography>
                </Paper>

                {/* Edge (if not last node) */}
                {nodeIndex < path.nodes.length - 1 && path.edges[nodeIndex] && (
                  <Box
                    sx={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: 0.5,
                    }}
                  >
                    <ArrowIcon sx={{ color: 'text.secondary', fontSize: 28 }} />
                    <Chip
                      label={path.edges[nodeIndex].relation_type}
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: '0.65rem',
                        bgcolor: 'rgba(59, 130, 246, 0.12)',
                        color: '#3B82F6',
                        fontWeight: 600,
                      }}
                    />
                    <Typography
                      variant="caption"
                      sx={{
                        fontSize: '0.65rem',
                        color: 'text.secondary',
                        fontFamily: 'monospace',
                      }}
                    >
                      {(path.edges[nodeIndex].confidence * 100).toFixed(0)}%
                    </Typography>
                  </Box>
                )}
              </React.Fragment>
            ))}
          </Box>

          {/* Path Description */}
          <Box sx={{ mt: 3, p: 2, bgcolor: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 0.5, display: 'block' }}>
              PATH DESCRIPTION
            </Typography>
            <Typography variant="body2" sx={{ fontSize: '0.8rem', lineHeight: 1.6 }}>
              {path.nodes.map((node, i) => (
                <React.Fragment key={i}>
                  <strong>{node.label}</strong>
                  {i < path.nodes.length - 1 && path.edges[i] && (
                    <>
                      {' '}
                      <span style={{ color: '#3B82F6' }}>{path.edges[i].relation_type.toLowerCase().replace(/_/g, ' ')}</span>
                      {' '}
                    </>
                  )}
                </React.Fragment>
              ))}
            </Typography>
          </Box>
        </Paper>
      ))}
    </Box>
  );
};
