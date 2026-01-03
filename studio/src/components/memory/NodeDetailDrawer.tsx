import React, { useState } from 'react';
import { Drawer, Box, Typography, IconButton, Tabs, Tab, Chip, Paper, Divider, Button } from '@mui/material';
import {
  Close as CloseIcon,
  Timeline as TimelineIcon,
  AccountTree as GraphIcon,
  Analytics as AnalyticsIcon,
  Code as CodeIcon,
  History as HistoryIcon,
} from '@mui/icons-material';

interface NodeDetailDrawerProps {
  open: boolean;
  node: any;
  onClose: () => void;
  onNavigateToNode?: (nodeId: string) => void;
  onTraceRelationship?: (sourceId: string, targetId: string) => void;
}

export const NodeDetailDrawer: React.FC<NodeDetailDrawerProps> = ({
  open,
  node,
  onClose,
  onNavigateToNode,
  onTraceRelationship,
}) => {
  const [activeTab, setActiveTab] = useState<'properties' | 'connections' | 'analytics' | 'history'>('properties');

  if (!node) return null;

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      sx={{
        '& .MuiDrawer-paper': {
          width: { xs: '100%', sm: 600 },
          bgcolor: 'background.default',
        },
      }}
    >
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <Box sx={{ p: 3, borderBottom: '1px solid', borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
            <Box sx={{ flex: 1 }}>
              <Chip
                label={node.type?.toUpperCase()}
                size="small"
                sx={{
                  mb: 1,
                  bgcolor: 'rgba(139, 92, 246, 0.12)',
                  color: '#8B5CF6',
                  border: '1px solid rgba(139, 92, 246, 0.3)',
                  fontWeight: 700,
                  fontSize: '0.7rem',
                }}
              />
              <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
                {node.label}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}>
                ID: {node.id}
              </Typography>
            </Box>
            <IconButton onClick={onClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>

          {/* Quick Stats */}
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1.5, mt: 2 }}>
            <Paper sx={{ p: 1.5, borderRadius: '8px', bgcolor: 'rgba(59, 130, 246, 0.08)' }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                CONNECTIONS
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#3B82F6' }}>
                {node.connections || 0}
              </Typography>
            </Paper>
            <Paper sx={{ p: 1.5, borderRadius: '8px', bgcolor: 'rgba(16, 185, 129, 0.08)' }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                IMPORTANCE
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#10B981' }}>
                {((node.importance || 0) * 100).toFixed(0)}%
              </Typography>
            </Paper>
            <Paper sx={{ p: 1.5, borderRadius: '8px', bgcolor: 'rgba(245, 158, 11, 0.08)' }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                CONFIDENCE
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#F59E0B' }}>
                {((node.confidence || 0.9) * 100).toFixed(0)}%
              </Typography>
            </Paper>
          </Box>
        </Box>

        {/* Tabs */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 3 }}>
          <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)}>
            <Tab icon={<CodeIcon fontSize="small" />} label="Properties" value="properties" sx={{ textTransform: 'none', minHeight: 48 }} />
            <Tab icon={<GraphIcon fontSize="small" />} label="Connections" value="connections" sx={{ textTransform: 'none', minHeight: 48 }} />
            <Tab icon={<AnalyticsIcon fontSize="small" />} label="Analytics" value="analytics" sx={{ textTransform: 'none', minHeight: 48 }} />
            <Tab icon={<HistoryIcon fontSize="small" />} label="History" value="history" sx={{ textTransform: 'none', minHeight: 48 }} />
          </Tabs>
        </Box>

        {/* Content */}
        <Box sx={{ flex: 1, overflow: 'auto', p: 3 }}>
          {activeTab === 'properties' && (
            <Box>
              {/* Core Properties */}
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, textTransform: 'uppercase', fontSize: '0.75rem' }}>
                Core Properties
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mb: 3 }}>
                {[
                  { key: 'Created', value: node.created_at || 'Unknown' },
                  { key: 'Updated', value: node.updated_at || 'Unknown' },
                  { key: 'Valid From', value: node.valid_from || 'N/A' },
                  { key: 'Valid Until', value: node.valid_until || 'Current' },
                  { key: 'Is Current', value: node.is_current ? 'Yes' : 'No' },
                  { key: 'Canonical ID', value: node.canonical_id || 'N/A' },
                ].map((prop) => (
                  <Box key={prop.key} sx={{ display: 'flex', justifyContent: 'space-between', p: 1.5, bgcolor: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                    <Typography variant="body2" sx={{ fontSize: '0.8rem', color: 'text.secondary' }}>
                      {prop.key}
                    </Typography>
                    <Typography variant="body2" sx={{ fontSize: '0.8rem', fontWeight: 600, fontFamily: 'monospace' }}>
                      {prop.value}
                    </Typography>
                  </Box>
                ))}
              </Box>

              {/* Custom Properties */}
              {node.properties && Object.keys(node.properties).length > 0 && (
                <>
                  <Divider sx={{ my: 3 }} />
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, textTransform: 'uppercase', fontSize: '0.75rem' }}>
                    Custom Properties ({Object.keys(node.properties).length})
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                    {Object.entries(node.properties).map(([key, value]) => (
                      <Box key={key} sx={{ p: 1.5, bgcolor: 'rgba(139, 92, 246, 0.08)', borderRadius: '8px', border: '1px solid rgba(139, 92, 246, 0.2)' }}>
                        <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', mb: 0.5, display: 'block' }}>
                          {key}
                        </Typography>
                        <Typography variant="body2" sx={{ fontSize: '0.85rem', fontWeight: 600, fontFamily: typeof value === 'number' ? 'monospace' : 'inherit', wordBreak: 'break-word' }}>
                          {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </>
              )}

              {/* Source Text */}
              {node.source_text && (
                <>
                  <Divider sx={{ my: 3 }} />
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, textTransform: 'uppercase', fontSize: '0.75rem' }}>
                    Source Text
                  </Typography>
                  <Paper sx={{ p: 2, bgcolor: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                    <Typography variant="body2" sx={{ fontSize: '0.85rem', fontStyle: 'italic', lineHeight: 1.6 }}>
                      "{node.source_text}"
                    </Typography>
                  </Paper>
                </>
              )}

              {/* Aliases */}
              {node.aliases && node.aliases.length > 0 && (
                <>
                  <Divider sx={{ my: 3 }} />
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, textTransform: 'uppercase', fontSize: '0.75rem' }}>
                    Aliases
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {node.aliases.map((alias: string) => (
                      <Chip
                        key={alias}
                        label={alias}
                        size="small"
                        sx={{
                          bgcolor: 'rgba(59, 130, 246, 0.12)',
                          color: '#3B82F6',
                          border: '1px solid rgba(59, 130, 246, 0.2)',
                        }}
                      />
                    ))}
                  </Box>
                </>
              )}
            </Box>
          )}

          {activeTab === 'connections' && (
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, textTransform: 'uppercase', fontSize: '0.75rem' }}>
                Connected Nodes
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3, fontSize: '0.85rem' }}>
                This node has {node.connections || 0} connections. Click to navigate or trace relationships.
              </Typography>

              {/* Placeholder for connections - would be fetched from API */}
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {[
                  { id: '2', label: 'English Practice', type: 'PROJECT', relation: 'WORKING_ON', direction: 'outgoing' },
                  { id: '3', label: 'Become Fluent', type: 'GOAL', relation: 'HAS_GOAL', direction: 'outgoing' },
                  { id: '6', label: 'Language Learning', type: 'INTEREST', relation: 'INTERESTED_IN', direction: 'outgoing' },
                ].map((conn) => (
                  <Paper
                    key={conn.id}
                    sx={{
                      p: 2,
                      borderRadius: '12px',
                      border: '1px solid',
                      borderColor: 'divider',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      '&:hover': {
                        borderColor: 'primary.main',
                        transform: 'translateX(4px)',
                      },
                    }}
                    onClick={() => onNavigateToNode?.(conn.id)}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {conn.label}
                      </Typography>
                      <Chip
                        label={conn.type}
                        size="small"
                        sx={{
                          height: 20,
                          fontSize: '0.65rem',
                          bgcolor: 'rgba(139, 92, 246, 0.12)',
                          color: '#8B5CF6',
                        }}
                      />
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip
                        label={conn.relation}
                        size="small"
                        sx={{
                          height: 18,
                          fontSize: '0.6rem',
                          bgcolor: 'rgba(59, 130, 246, 0.12)',
                          color: '#3B82F6',
                        }}
                      />
                      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                        {conn.direction === 'outgoing' ? '→' : '←'}
                      </Typography>
                    </Box>
                    <Button
                      size="small"
                      sx={{ mt: 1, textTransform: 'none', fontSize: '0.75rem' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onTraceRelationship?.(node.id, conn.id);
                      }}
                    >
                      Trace Path
                    </Button>
                  </Paper>
                ))}
              </Box>

              <Button
                fullWidth
                variant="outlined"
                sx={{ mt: 3, textTransform: 'none' }}
                startIcon={<GraphIcon />}
              >
                View Full Neighborhood
              </Button>
            </Box>
          )}

          {activeTab === 'analytics' && (
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 3, textTransform: 'uppercase', fontSize: '0.75rem' }}>
                Node Analytics
              </Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {/* PageRank */}
                <Paper sx={{ p: 2.5, borderRadius: '12px', bgcolor: 'rgba(139, 92, 246, 0.08)', border: '1px solid rgba(139, 92, 246, 0.2)' }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                    PAGERANK SCORE
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: '#8B5CF6', mb: 1 }}>
                    {(node.pagerank_score || 0.85).toFixed(3)}
                  </Typography>
                  <Typography variant="body2" sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                    Importance ranking based on incoming connections. Higher = more central to graph.
                  </Typography>
                </Paper>

                {/* Centrality */}
                <Paper sx={{ p: 2.5, borderRadius: '12px', bgcolor: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                    DEGREE CENTRALITY
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: '#3B82F6', mb: 1 }}>
                    {(node.centrality_score || 0.72).toFixed(3)}
                  </Typography>
                  <Typography variant="body2" sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                    Normalized connection count. Measures direct influence in the network.
                  </Typography>
                </Paper>

                {/* Community */}
                <Paper sx={{ p: 2.5, borderRadius: '12px', bgcolor: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                    COMMUNITY
                  </Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700, color: '#10B981', mb: 1 }}>
                    Learning Cluster
                  </Typography>
                  <Typography variant="body2" sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                    Part of a detected relationship cluster with 8 other nodes.
                  </Typography>
                </Paper>
              </Box>
            </Box>
          )}

          {activeTab === 'history' && (
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 3, textTransform: 'uppercase', fontSize: '0.75rem' }}>
                Version History
              </Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {[
                  { version: 3, date: '2024-12-27', change: 'Updated progress to 60%', reason: 'user_update' },
                  { version: 2, date: '2024-12-20', change: 'Changed status to active', reason: 'new_information' },
                  { version: 1, date: '2024-12-15', change: 'Initial creation', reason: 'extraction' },
                ].map((hist) => (
                  <Paper
                    key={hist.version}
                    sx={{
                      p: 2,
                      borderRadius: '12px',
                      border: '1px solid',
                      borderColor: 'divider',
                      position: 'relative',
                      '&::before': {
                        content: '""',
                        position: 'absolute',
                        left: 16,
                        top: '100%',
                        width: 2,
                        height: 16,
                        bgcolor: 'divider',
                      },
                      '&:last-child::before': {
                        display: 'none',
                      },
                    }}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Chip
                        label={`v${hist.version}`}
                        size="small"
                        sx={{
                          height: 20,
                          fontSize: '0.65rem',
                          fontWeight: 700,
                          bgcolor: hist.version === 3 ? 'rgba(16, 185, 129, 0.12)' : 'rgba(148, 163, 184, 0.12)',
                          color: hist.version === 3 ? '#10B981' : '#94A3B8',
                        }}
                      />
                      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                        {hist.date}
                      </Typography>
                    </Box>
                    <Typography variant="body2" sx={{ fontSize: '0.85rem', mb: 0.5 }}>
                      {hist.change}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                      Reason: {hist.reason}
                    </Typography>
                  </Paper>
                ))}
              </Box>

              <Button
                fullWidth
                variant="outlined"
                sx={{ mt: 3, textTransform: 'none' }}
                startIcon={<TimelineIcon />}
              >
                View Full Timeline
              </Button>
            </Box>
          )}
        </Box>
      </Box>
    </Drawer>
  );
};
