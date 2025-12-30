import React, { useState, useMemo, useCallback, useRef, useEffect, memo } from 'react';
import { Box, Typography, Chip, IconButton, Tooltip, Paper, Select, MenuItem, FormControl, InputLabel, Drawer } from '@mui/material';
import {
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  CenterFocusStrong as CenterIcon,
  Refresh as RefreshIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import ForceGraph2D from 'react-force-graph-2d';

export interface GraphNode {
  id: string;
  label: string;
  type: 'person' | 'organization' | 'location' | 'event' | 'project' | 'goal' | 'task' | 'activity' | 'interest' | 'priority' | 'skill' | 'topic' | 'product';
  connections: number;
  importance: number;
  is_current?: number;
  properties?: {
    status?: string;
    progress?: number;
    is_current?: boolean;
  };
}

export interface GraphEdge {
  source: string;
  target: string;
  relation_type: string;
  strength: number;
  is_current?: number;
  properties?: Record<string, any>;
}

interface KnowledgeGraphVisualizationProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (node: GraphNode) => void;
}

const nodeColors: Record<string, string> = {
  person: '#3B82F6',
  organization: '#8B5CF6',
  location: '#10B981',
  event: '#EC4899',
  product: '#06B6D4',
  skill: '#F59E0B',
  topic: '#3B82F6',
  project: '#8B5CF6',
  goal: '#10B981',
  task: '#3B82F6',
  activity: '#F59E0B',
  interest: '#EC4899',
  priority: '#EF4444',
  document: '#64748B',
};

type LayoutType = 'force';

export const KnowledgeGraphVisualization: React.FC<KnowledgeGraphVisualizationProps> = ({
  nodes,
  edges,
  onNodeClick,
}) => {
  const fgRef = useRef<any>(null);
  const [layoutType, setLayoutType] = useState<LayoutType>('force');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<GraphEdge | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const [dagError, setDagError] = useState<string | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  
  // Cache graphData to prevent re-renders
  const graphDataRef = useRef<any>(null);
  const nodeIdsRef = useRef<string>('');
  const edgeIdsRef = useRef<string>('');

  // Convert to react-force-graph format with stable references
  const graphData = useMemo(() => {
    // Create stable ID strings for comparison
    const currentNodeIds = nodes.map(n => n.id).sort().join(',');
    const currentEdgeIds = edges.map(e => `${e.source}-${e.target}`).sort().join(',');
    
    // If IDs haven't changed, return cached data
    if (currentNodeIds === nodeIdsRef.current && 
        currentEdgeIds === edgeIdsRef.current && 
        graphDataRef.current) {
      return graphDataRef.current;
    }
    
    // IDs changed, create new graph data
    nodeIdsRef.current = currentNodeIds;
    edgeIdsRef.current = currentEdgeIds;
    
    const newGraphData = {
      nodes: nodes.map(node => ({
        ...node,
        id: node.id,
        name: node.label,
        val: 15 + (node.importance * 45),
        color: nodeColors[node.type] || '#64748B',
      })),
      links: edges.map(edge => ({
        ...edge,
        source: edge.source,
        target: edge.target,
        label: edge.relation_type,
      })),
    };
    
    graphDataRef.current = newGraphData;
    return newGraphData;
  }, [nodes, edges]);

  // Configure forces and initial zoom after graph loads
  useEffect(() => {
    if (fgRef.current) {
      const fg = fgRef.current;
      
      // Configure forces after a delay
      setTimeout(() => {
        if (fg) {
          // Configure stronger forces for better spacing
          fg.d3Force('charge').strength(-400);
          fg.d3Force('link').distance(100);
          
          // Add collision force to prevent overlap
          const d3 = require('d3-force');
          fg.d3Force('collide', d3.forceCollide().radius((node: any) => {
            return Math.sqrt(node.val || 20) * 1.5 + 15;
          }).strength(0.9));
          
          // Reheat simulation to apply new forces
          fg.d3ReheatSimulation();
          
          // Center camera on graph and zoom after layout stabilizes
          setTimeout(() => {
            fg.zoomToFit(400);
            setTimeout(() => {
              const currentZoom = fg.zoom();
              setZoomLevel(currentZoom);
            }, 450);
          }, 500);
        }
      }, 200);
    }
  }, [graphData]);

  const handleNodeClick = useCallback((node: any) => {
    setSelectedNode(node);
    setDetailDrawerOpen(true);
    onNodeClick?.(node);
  }, [onNodeClick]);

  const handleNodeHover = useCallback((node: any) => {
    setHoveredNode(node);
  }, []);

  const handleLinkHover = useCallback((link: any) => {
    setHoveredEdge(link);
  }, []);
  
  // Track mouse position for tooltip
  const handleMouseMove = useCallback((event: React.MouseEvent) => {
    if (hoveredNode || hoveredEdge) {
      setTooltipPosition({ x: event.clientX, y: event.clientY });
    }
  }, [hoveredNode, hoveredEdge]);

  const handleDagError = useCallback((loopNodeIds: (string | number)[]) => {
    console.warn('DAG layout failed due to cycle:', loopNodeIds);
    setDagError(`Graph contains cycles - hierarchical layouts require acyclic graphs. Reverting to force-directed layout.`);
    setLayoutType('force');
    // Clear error after 5 seconds
    setTimeout(() => setDagError(null), 5000);
  }, []);

  const handleZoomIn = () => {
    if (fgRef.current) {
      const zoom = fgRef.current.zoom();
      const newZoom = zoom * 1.5;
      fgRef.current.zoom(newZoom, 400);
      setZoomLevel(newZoom);
    }
  };

  const handleZoomOut = () => {
    if (fgRef.current) {
      const zoom = fgRef.current.zoom();
      const newZoom = zoom / 1.5;
      fgRef.current.zoom(newZoom, 400);
      setZoomLevel(newZoom);
    }
  };

  const handleCenter = () => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(400);
      setTimeout(() => {
        if (fgRef.current) {
          setZoomLevel(fgRef.current.zoom());
        }
      }, 450);
    }
  };

  const closeDetailDrawer = () => {
    setDetailDrawerOpen(false);
  };

  return (
    <Box sx={{ position: 'relative', height: '600px' }}>

      {/* Legend & Layout Selector */}
      <Paper
        sx={{
          position: 'absolute',
          top: 16,
          left: 16,
          p: 2,
          borderRadius: '12px',
          bgcolor: 'rgba(0, 0, 0, 0.6)',
          backdropFilter: 'blur(12px)',
          zIndex: 10,
          maxHeight: '500px',
          overflowY: 'auto',
        }}
      >
        {/* Layout Selector */}
        <Box sx={{ mb: 2, px: 1 }}>
          <Typography variant="caption" sx={{ 
            fontSize: '0.7rem', 
            fontWeight: 600, 
            color: 'rgba(255,255,255,0.9)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em'
          }}>
            Layout: Force-Directed
          </Typography>
          <Typography variant="caption" sx={{ 
            fontSize: '0.65rem', 
            color: 'rgba(255,255,255,0.5)',
            display: 'block',
            mt: 0.5
          }}>
            Optimized for cyclic graphs
          </Typography>
        </Box>
        <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600, mb: 1, display: 'block' }}>
          NODE TYPES
        </Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0.5, mb: 1 }}>
          {Object.entries(nodeColors).map(([type, color]) => (
            <Box key={type} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box
                sx={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  bgcolor: color,
                  boxShadow: `0 0 6px ${color}60`,
                }}
              />
              <Typography variant="caption" sx={{ fontSize: '0.65rem', textTransform: 'capitalize' }}>
                {type}
              </Typography>
            </Box>
          ))}
        </Box>
        <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
          <Typography variant="caption" sx={{ fontSize: '0.65rem', fontWeight: 600, color: 'rgba(255,255,255,0.6)', mb: 1, display: 'block' }}>
            Status
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
            <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: '#3B82F6', border: '2px solid #3B82F6' }} />
            <Typography variant="caption" sx={{ fontSize: '0.65rem' }}>Current (solid)</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: 'transparent', border: '2px dashed rgba(59, 130, 246, 0.5)' }} />
            <Typography variant="caption" sx={{ fontSize: '0.65rem' }}>Historical (dashed, faded)</Typography>
          </Box>
        </Box>
      </Paper>

      {/* Error Toast - Glassmorphic */}
      {dagError && (
        <Paper
          sx={{
            position: 'absolute',
            top: 24,
            left: '50%',
            transform: 'translateX(-50%)',
            px: 3,
            py: 2,
            borderRadius: '16px',
            background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.15) 100%)',
            backdropFilter: 'blur(20px) saturate(180%)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            boxShadow: '0 8px 32px 0 rgba(239, 68, 68, 0.2), inset 0 1px 0 0 rgba(255, 255, 255, 0.1)',
            zIndex: 1001,
            maxWidth: 500,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{ 
              width: 8, 
              height: 8, 
              borderRadius: '50%', 
              bgcolor: '#EF4444',
              boxShadow: '0 0 12px rgba(239, 68, 68, 0.6)'
            }} />
            <Typography variant="body2" sx={{ color: '#fff', fontWeight: 500, fontSize: '0.875rem' }}>
              {dagError}
            </Typography>
          </Box>
        </Paper>
      )}

      {/* Zoom Controls */}
      <Box
        sx={{
          position: 'absolute',
          top: 16,
          right: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 1,
          zIndex: 10,
        }}
      >
        <Tooltip title="Zoom In" placement="left">
          <IconButton
            size="small"
            onClick={handleZoomIn}
            sx={{
              bgcolor: 'rgba(0, 0, 0, 0.6)',
              backdropFilter: 'blur(12px)',
              color: 'white',
              '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.8)' },
            }}
          >
            <ZoomInIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Zoom Out" placement="left">
          <IconButton
            size="small"
            onClick={handleZoomOut}
            sx={{
              bgcolor: 'rgba(0, 0, 0, 0.6)',
              backdropFilter: 'blur(12px)',
              color: 'white',
              '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.8)' },
            }}
          >
            <ZoomOutIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Fit to View" placement="left">
          <IconButton
            size="small"
            onClick={handleCenter}
            sx={{
              bgcolor: 'rgba(0, 0, 0, 0.6)',
              backdropFilter: 'blur(12px)',
              color: 'white',
              '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.8)' },
            }}
          >
            <CenterIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        
        {/* Zoom Level Indicator */}
        <Paper
          sx={{
            mt: 1,
            px: 1.5,
            py: 0.5,
            borderRadius: '8px',
            bgcolor: 'rgba(0, 0, 0, 0.6)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
          }}
        >
          <Typography variant="caption" sx={{ color: 'white', fontSize: '0.7rem', fontWeight: 600 }}>
            {(zoomLevel * 100).toFixed(0)}%
          </Typography>
        </Paper>
      </Box>

      {/* Custom Tooltip - Smart Positioning */}
      {(hoveredNode || hoveredEdge) && React.createElement(() => {
        const offset = 20;
        const tooltipWidth = 250;
        const tooltipHeight = 150;
        
        let x = tooltipPosition.x + offset;
        let y = tooltipPosition.y + offset;
        
        if (x + tooltipWidth > window.innerWidth - 20) {
          x = tooltipPosition.x - tooltipWidth - offset;
        }
        
        if (y + tooltipHeight > window.innerHeight - 20) {
          y = tooltipPosition.y - tooltipHeight - offset;
        }
        
        x = Math.max(10, x);
        y = Math.max(10, y);
        
        return (
          <Paper
            sx={{
              position: 'fixed',
              top: y,
              left: x,
              p: 2,
              borderRadius: '12px',
              bgcolor: 'rgba(0, 0, 0, 0.9)',
              backdropFilter: 'blur(12px)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              zIndex: 1000,
              pointerEvents: 'none',
              minWidth: 200,
              maxWidth: 300,
            }}
          >
          {hoveredNode && (
            <Box>
              <Typography variant="h6" sx={{ fontSize: '1rem', fontWeight: 600, mb: 1, color: '#fff' }}>
                {hoveredNode.label}
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>Type:</Typography>
                  <Chip
                    label={hoveredNode.type || 'unknown'}
                    size="small"
                    sx={{
                      height: 20,
                      fontSize: '0.65rem',
                      bgcolor: nodeColors[hoveredNode.type] || '#64748B',
                      color: '#fff',
                      textTransform: 'capitalize',
                    }}
                  />
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>Status:</Typography>
                  <Typography variant="caption" sx={{ color: '#fff', fontWeight: 600 }}>
                    {hoveredNode.is_current === 1 ? 'Current' : 'Historical'}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>Connections:</Typography>
                  <Typography variant="caption" sx={{ color: '#fff', fontWeight: 600 }}>
                    {hoveredNode.connections || 0}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>Importance:</Typography>
                  <Typography variant="caption" sx={{ color: '#fff', fontWeight: 600 }}>
                    {(hoveredNode.importance * 100 || 0).toFixed(0)}%
                  </Typography>
                </Box>
              </Box>
            </Box>
          )}
          {hoveredEdge && (
            <Box>
              <Typography variant="h6" sx={{ fontSize: '1rem', fontWeight: 600, mb: 1, color: '#fff' }}>
                {hoveredEdge.relation_type}
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>From:</Typography>
                  <Typography variant="caption" sx={{ color: '#fff', fontWeight: 600 }}>
                    {typeof hoveredEdge.source === 'object' ? (hoveredEdge.source as any).name : nodes.find(n => n.id === hoveredEdge.source)?.label || hoveredEdge.source}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>To:</Typography>
                  <Typography variant="caption" sx={{ color: '#fff', fontWeight: 600 }}>
                    {typeof hoveredEdge.target === 'object' ? (hoveredEdge.target as any).name : nodes.find(n => n.id === hoveredEdge.target)?.label || hoveredEdge.target}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>Status:</Typography>
                  <Typography variant="caption" sx={{ color: '#fff', fontWeight: 600 }}>
                    {hoveredEdge.is_current === 1 ? 'Current' : 'Historical'}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>Strength:</Typography>
                  <Typography variant="caption" sx={{ color: '#fff', fontWeight: 600 }}>
                    {(hoveredEdge.strength * 100 || 0).toFixed(0)}%
                  </Typography>
                </Box>
              </Box>
            </Box>
          )}
        </Paper>
        );
      })}

      {/* Graph Canvas */}
      <Box
        onMouseMove={handleMouseMove}
        sx={{
          width: '100%',
          height: '100%',
          borderRadius: '20px',
          overflow: 'hidden',
          background: 'linear-gradient(135deg, rgba(30, 27, 75, 0.95) 0%, rgba(15, 23, 42, 0.95) 50%, rgba(20, 30, 48, 0.95) 100%)',
          boxShadow: 'inset 0 1px 0 0 rgba(255, 255, 255, 0.05)',
        }}
      >
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          width={1200}
          height={600}
          backgroundColor="rgba(0,0,0,0)"
          dagMode={layoutType === 'force' ? undefined : layoutType}
          dagLevelDistance={50}
          onDagError={handleDagError}
          nodeLabel="name"
          nodeVal="val"
          nodeColor={(node: any) => {
            const isCurrent = node.is_current === 1;
            const baseColor = node.color || '#64748B';
            return isCurrent ? baseColor : `${baseColor}80`;
          }}
          nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
            // Skip if node position is not yet calculated
            if (!node.x || !node.y || !isFinite(node.x) || !isFinite(node.y)) {
              return;
            }
            
            const label = node.name;
            const fontSize = Math.max(12 / globalScale, 10);
            const isCurrent = node.is_current === 1;
            const nodeRadius = Math.sqrt(node.val || 20) * 1.2;
            
            // Draw glow effect for current nodes
            if (isCurrent) {
              ctx.beginPath();
              ctx.arc(node.x, node.y, nodeRadius + 4, 0, 2 * Math.PI);
              const gradient = ctx.createRadialGradient(node.x, node.y, nodeRadius, node.x, node.y, nodeRadius + 4);
              gradient.addColorStop(0, `${node.color}40`);
              gradient.addColorStop(1, 'transparent');
              ctx.fillStyle = gradient;
              ctx.fill();
            }
            
            // Draw node circle
            ctx.beginPath();
            ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI);
            ctx.fillStyle = node.color || '#64748B';
            ctx.globalAlpha = isCurrent ? 1 : 0.3;
            ctx.fill();
            ctx.globalAlpha = 1;
            
            // Draw border
            ctx.strokeStyle = node.color || '#64748B';
            ctx.lineWidth = 2 / globalScale;
            if (!isCurrent) {
              ctx.setLineDash([5 / globalScale, 3 / globalScale]);
            }
            ctx.stroke();
            ctx.setLineDash([]);
            
            // Draw label with background for better readability
            if (globalScale > 0.8) {
              ctx.font = `600 ${fontSize}px Inter, sans-serif`;
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              
              const labelY = node.y + nodeRadius + fontSize + 4;
              const textMetrics = ctx.measureText(label);
              const padding = 6;
              
              // Draw label background
              ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
              ctx.fillRect(
                node.x - textMetrics.width / 2 - padding,
                labelY - fontSize / 2 - padding / 2,
                textMetrics.width + padding * 2,
                fontSize + padding
              );
              
              // Draw label text
              ctx.fillStyle = isCurrent ? '#ffffff' : 'rgba(255, 255, 255, 0.6)';
              ctx.fillText(label, node.x, labelY);
            }
          }}
          linkColor={(link: any) => {
            const isCurrent = link.is_current === 1;
            return isCurrent ? 'rgba(148, 163, 184, 0.6)' : 'rgba(148, 163, 184, 0.2)';
          }}
          linkWidth={(link: any) => Math.max(link.strength * 4, 1)}
          linkDirectionalParticles={3}
          linkDirectionalParticleWidth={(link: any) => link.is_current === 1 ? 3 : 0}
          onNodeClick={handleNodeClick}
          onNodeHover={handleNodeHover}
          onLinkHover={handleLinkHover}
          enableNodeDrag={true}
          enableZoomInteraction={true}
          enablePanInteraction={true}
          d3AlphaDecay={0.015}
          d3VelocityDecay={0.2}
          cooldownTicks={150}
          warmupTicks={50}
        />
      </Box>

      {/* Stats */}
      <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
        <Chip
          label={`${nodes.length} Nodes`}
          sx={{
            bgcolor: 'rgba(59, 130, 246, 0.12)',
            color: '#3B82F6',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            fontWeight: 600,
          }}
        />
        <Chip
          label={`${edges.length} Edges`}
          sx={{
            bgcolor: 'rgba(139, 92, 246, 0.12)',
            color: '#8B5CF6',
            border: '1px solid rgba(139, 92, 246, 0.3)',
            fontWeight: 600,
          }}
        />
      </Box>

      {/* Detail Drawer */}
      <Drawer
        anchor="right"
        open={detailDrawerOpen}
        onClose={closeDetailDrawer}
        sx={{
          '& .MuiDrawer-paper': {
            width: 420,
            height: 'calc(100vh - 32px)',
            margin: '16px',
            background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.85) 0%, rgba(30, 41, 59, 0.85) 100%)',
            backdropFilter: 'blur(20px) saturate(180%)',
            borderLeft: '1px solid rgba(255, 255, 255, 0.1)',
            boxShadow: '-8px 0 32px 0 rgba(0, 0, 0, 0.4)',
            borderRadius: '8px',
            overflow: 'hidden',
          },
        }}
      >
        {selectedNode && (
          <Box sx={{ p: 3, height: '100%', overflowY: 'auto', overflowX: 'hidden' }}>
            {/* Header - Glassmorphic */}
            <Box sx={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'flex-start', 
              mb: 3,
              pb: 3,
              borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
            }}>
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 600, mb: 1.5, fontSize: '1.5rem' }}>
                  {selectedNode.label}
                </Typography>
                <Chip
                  label={selectedNode.type}
                  size="small"
                  sx={{
                    bgcolor: `${nodeColors[selectedNode.type]}20`,
                    color: nodeColors[selectedNode.type],
                    border: `1px solid ${nodeColors[selectedNode.type]}40`,
                    textTransform: 'capitalize',
                    fontWeight: 600,
                    backdropFilter: 'blur(10px)',
                  }}
                />
              </Box>
              <IconButton 
                onClick={closeDetailDrawer} 
                size="small"
                sx={{
                  bgcolor: 'rgba(255, 255, 255, 0.05)',
                  backdropFilter: 'blur(10px)',
                  '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.1)' },
                }}
              >
                <CloseIcon />
              </IconButton>
            </Box>

            {/* Status Badge - Glassmorphic */}
            <Box sx={{ mb: 3 }}>
              <Chip
                label={selectedNode.is_current === 1 ? 'Current' : 'Historical'}
                sx={{
                  bgcolor: selectedNode.is_current === 1 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                  color: selectedNode.is_current === 1 ? '#10B981' : '#F59E0B',
                  border: `1px solid ${selectedNode.is_current === 1 ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
                  fontWeight: 600,
                  backdropFilter: 'blur(10px)',
                  fontSize: '0.75rem',
                  height: '24px',
                  borderRadius: '8px',
                  px: 1.5,
                  '& .MuiChip-label': {
                    px: 0,
                  },
                }}
              />
            </Box>

            {/* Metrics - Glassmorphic Cards */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Paper sx={{
                p: 2.5,
                borderRadius: '12px',
                background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.1) 100%)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(59, 130, 246, 0.2)',
              }}>
                <Typography variant="caption" sx={{ 
                  color: 'rgba(255,255,255,0.6)', 
                  textTransform: 'uppercase', 
                  fontSize: '0.65rem', 
                  fontWeight: 600,
                  letterSpacing: '0.05em'
                }}>
                  Connections
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 600, color: '#3B82F6', mt: 0.5 }}>
                  {selectedNode.connections}
                </Typography>
              </Paper>
              <Paper sx={{
                p: 2.5,
                borderRadius: '12px',
                background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(124, 58, 237, 0.1) 100%)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(139, 92, 246, 0.2)',
              }}>
                <Typography variant="caption" sx={{ 
                  color: 'rgba(255,255,255,0.6)', 
                  textTransform: 'uppercase', 
                  fontSize: '0.65rem', 
                  fontWeight: 600,
                  letterSpacing: '0.05em'
                }}>
                  Importance
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 600, color: '#8B5CF6', mt: 0.5 }}>
                  {(selectedNode.importance * 100).toFixed(0)}%
                </Typography>
              </Paper>
            </Box>

            {/* Properties - Glassmorphic */}
            {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="caption" sx={{ 
                  color: 'rgba(255,255,255,0.6)', 
                  textTransform: 'uppercase', 
                  fontSize: '0.65rem', 
                  fontWeight: 600, 
                  mb: 2, 
                  display: 'block',
                  letterSpacing: '0.05em'
                }}>
                  Properties
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {Object.entries(selectedNode.properties).map(([key, value]) => (
                    <Paper key={key} sx={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      p: 2, 
                      background: 'rgba(255,255,255,0.03)',
                      backdropFilter: 'blur(10px)',
                      border: '1px solid rgba(255,255,255,0.08)',
                      borderRadius: '10px',
                      transition: 'all 0.2s ease',
                      '&:hover': {
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid rgba(255,255,255,0.12)',
                      }
                    }}>
                      <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)', textTransform: 'capitalize', fontSize: '0.875rem' }}>
                        {key.replace(/_/g, ' ')}
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.875rem' }}>
                        {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)}
                      </Typography>
                    </Paper>
                  ))}
                </Box>
              </Box>
            )}
          </Box>
        )}
      </Drawer>
    </Box>
  );
};
