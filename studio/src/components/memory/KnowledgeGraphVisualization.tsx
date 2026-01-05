import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { Box, Typography, Chip, IconButton, Tooltip, Paper, Drawer, styled, CircularProgress } from '@mui/material';
import { fetchNodeHistory, NodeHistoryResponse, fetchTemporalGraphState, fetchChanges } from '../../api/kg';
import { ZoomIn as ZoomInIcon, ZoomOut as ZoomOutIcon, Focus as CenterIcon, X as CloseIcon, GitBranch as LayoutIcon } from 'lucide-react';
import ForceGraph2D from 'react-force-graph-2d';
import { TemporalControls } from './TemporalControls';

export interface GraphNode {
  id: string;
  label: string;
  type: 'person' | 'organization' | 'location' | 'event' | 'project' | 'goal' | 'task' | 'activity' | 'interest' | 'priority' | 'skill' | 'topic' | 'product';
  connections: number;
  importance: number;
  is_current?: number;
  canonical_id?: string;
  valid_from?: string;
  valid_until?: string | null;
  created_at?: string;
  updated_at?: string;
  properties?: {
    status?: string;
    progress?: number;
    is_current?: boolean;
    [key: string]: any;
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
  onTemporalStateChange?: (nodes: GraphNode[], edges: GraphEdge[], isLive: boolean) => void;
}

// Styled glassmorphic tooltip
const GlassmorphicTooltip = styled(({ className, ...props }: any) => (
  <Tooltip {...props} classes={{ popper: className }} />
))(({ theme }) => ({
  '& .MuiTooltip-tooltip': {
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    backdropFilter: 'blur(12px) saturate(180%)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '8px',
    padding: '8px 12px',
    fontSize: '0.75rem',
    fontWeight: 500,
    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
  },
  '& .MuiTooltip-arrow': {
    color: 'rgba(0, 0, 0, 0.85)',
    '&::before': {
      border: '1px solid rgba(255, 255, 255, 0.1)',
    },
  },
}));

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
  onTemporalStateChange,
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
  const [selectedNodeTypes, setSelectedNodeTypes] = useState<Set<string>>(new Set());
  const [hoveredLegendType, setHoveredLegendType] = useState<string | null>(null);
  const [nodeHistory, setNodeHistory] = useState<NodeHistoryResponse | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [activityData, setActivityData] = useState<Array<{ date: string; changeCount: number }>>([]);
  
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
          const d3 = require('d3-force');
          
          // Reduce charge strength to bring disconnected components closer
          fg.d3Force('charge').strength(-200);
          
          // Keep link distance reasonable for connected nodes
          fg.d3Force('link').distance(80);
          
          // Add strong center force to pull all nodes toward center
          // This prevents disconnected components from drifting far apart
          fg.d3Force('center', d3.forceCenter().strength(0.3));
          
          // Add collision force to prevent overlap
          fg.d3Force('collide', d3.forceCollide().radius((node: any) => {
            return Math.sqrt(node.val || 20) * 1.5 + 15;
          }).strength(0.9));
          
          // Add many-body force with reduced strength for better clustering
          fg.d3Force('charge').strength(-200).distanceMax(400);
          
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

  // Handle timeline scrubber changes
  const handleTimelineChange = useCallback(async (timestamp: string, isLive: boolean) => {
    
    if (isLive) {
      console.log('Returning to live view');
      if (onTemporalStateChange) {
        // Return to original live data
        onTemporalStateChange(nodes, edges, true);
      }
      return;
    }
    
    console.log('Fetching temporal graph state for:', timestamp);
    try {
      const temporalState = await fetchTemporalGraphState({ 
        as_of: timestamp, 
        include_edges: true,
        node_limit: 1000
      });
      
      console.log(`[TEMPORAL] Loaded temporal state: ${temporalState.total_nodes} nodes, ${temporalState.total_edges} edges`);
      
      // Transform temporal data to GraphNode/GraphEdge format
      const historicalNodes: GraphNode[] = temporalState.nodes.map(node => ({
        id: node.id,
        label: node.label,
        type: node.label.toLowerCase() as any, // Map label to type
        connections: 0, // Will be calculated
        importance: node.confidence * 100,
        is_current: node.is_current,
        canonical_id: node.canonical_id,
        valid_from: node.valid_from,
        valid_until: node.valid_until,
        created_at: node.created_at,
        updated_at: node.updated_at,
        properties: node.properties
      }));
      
      const historicalEdges: GraphEdge[] = temporalState.edges.map(edge => ({
        id: edge.id,
        source: edge.source_id,
        target: edge.target_id,
        relation_type: edge.relation_type,
        strength: edge.confidence,
        is_current: edge.is_current,
        properties: edge.properties
      }));
      
      console.log(`[TEMPORAL] Transformed to ${historicalNodes.length} nodes, ${historicalEdges.length} edges`);
      if (historicalEdges.length > 0) {
        console.log(`[TEMPORAL] Sample edge:`, historicalEdges[0]);
      }
      
      // Calculate connections for nodes
      historicalNodes.forEach(node => {
        node.connections = historicalEdges.filter(
          e => e.source === node.id || e.target === node.id
        ).length;
      });
      
      if (onTemporalStateChange) {
        onTemporalStateChange(historicalNodes, historicalEdges, false);
      }
      
    } catch (error) {
      console.error('Failed to fetch temporal graph state:', error);
    }
  }, [nodes, edges, onTemporalStateChange]);

  // Fetch activity data for heatmap on mount
  useEffect(() => {
    const fetchActivityData = async () => {
      try {
        const oneYearAgo = new Date();
        oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
        
        const changes = await fetchChanges(
          oneYearAgo.toISOString(),
          new Date().toISOString(),
          1000
        );
        
        // Group changes by date
        const activityMap = new Map<string, number>();
        changes.changes.forEach(change => {
          const date = change.timestamp.split('T')[0];
          activityMap.set(date, (activityMap.get(date) || 0) + 1);
        });
        
        const activity = Array.from(activityMap.entries()).map(([date, changeCount]) => ({
          date,
          changeCount
        }));
        
        setActivityData(activity);
      } catch (error) {
        console.error('Failed to fetch activity data:', error);
      }
    };
    
    fetchActivityData();
  }, []);

  const handleNodeClick = useCallback(async (node: any) => {
    setSelectedNode(node);
    setDetailDrawerOpen(true);
    setNodeHistory(null);
    
    // Fetch version history if node has an ID
    if (node.id) {
      setLoadingHistory(true);
      try {
        const history = await fetchNodeHistory(node.id);
        setNodeHistory(history);
      } catch (error) {
        console.error('Failed to fetch node history:', error);
      } finally {
        setLoadingHistory(false);
      }
    }
    
    if (onNodeClick) {
      onNodeClick(node);
    }
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

  const handleReLayout = () => {
    if (fgRef.current && graphData) {
      const fg = fgRef.current;
      const d3 = require('d3-force');
      
      // Calculate center of mass for all nodes
      let centerX = 0, centerY = 0;
      let nodeCount = 0;
      if (graphData.nodes.length > 0) {
        graphData.nodes.forEach((node: any) => {
          if (node.x && node.y && isFinite(node.x) && isFinite(node.y)) {
            centerX += node.x;
            centerY += node.y;
            nodeCount++;
          }
        });
        if (nodeCount > 0) {
          centerX /= nodeCount;
          centerY /= nodeCount;
        }
      }
      
      // Apply moderate centering forces during re-layout
      fg.d3Force('center', d3.forceCenter(centerX, centerY).strength(0.6));
      
      // Add weak X and Y positioning forces to prevent drift without bunching
      fg.d3Force('x', d3.forceX(centerX).strength(0.05));
      fg.d3Force('y', d3.forceY(centerY).strength(0.05));
      
      // Keep normal charge for good spacing
      fg.d3Force('charge').strength(-200);
      
      // Reheat simulation
      fg.d3ReheatSimulation();
      
      // Gradually reduce positioning forces
      setTimeout(() => {
        if (fg) {
          fg.d3Force('x', d3.forceX(centerX).strength(0.02));
          fg.d3Force('y', d3.forceY(centerY).strength(0.02));
        }
      }, 1000);
      
      setTimeout(() => {
        if (fg) {
          // Remove positioning forces and restore normal configuration
          fg.d3Force('x', null);
          fg.d3Force('y', null);
          fg.d3Force('center', d3.forceCenter().strength(0.3));
        }
      }, 2500);
      
      // Fit to view after layout settles
      setTimeout(() => {
        if (fg) {
          fg.zoomToFit(400);
          setTimeout(() => {
            if (fg) {
              setZoomLevel(fg.zoom());
            }
          }, 450);
        }
      }, 3000);
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
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600 }}>
            NODE TYPES
          </Typography>
          {selectedNodeTypes.size > 0 && (
            <IconButton
              size="small"
              onClick={() => setSelectedNodeTypes(new Set())}
              sx={{
                p: 0.5,
                bgcolor: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '6px',
                transition: 'all 0.2s ease',
                '&:hover': {
                  bgcolor: 'rgba(239, 68, 68, 0.25)',
                  transform: 'scale(1.05)',
                  boxShadow: '0 0 12px rgba(239, 68, 68, 0.4)',
                },
              }}
            >
              <CloseIcon sx={{ fontSize: 12, color: '#EF4444' }} />
            </IconButton>
          )}
        </Box>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0.5, mb: 1 }}>
          {Object.entries(nodeColors).map(([type, color]) => {
            const isSelected = selectedNodeTypes.has(type);
            const isHovered = hoveredLegendType === type;
            
            return (
              <Box
                key={type}
                onMouseEnter={() => setHoveredLegendType(type)}
                onMouseLeave={() => setHoveredLegendType(null)}
                onClick={() => {
                  const newSelected = new Set(selectedNodeTypes);
                  if (newSelected.has(type)) {
                    newSelected.delete(type);
                  } else {
                    newSelected.add(type);
                  }
                  setSelectedNodeTypes(newSelected);
                }}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  px: 1,
                  py: 0.5,
                  borderRadius: '6px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  bgcolor: isSelected ? `${color}20` : 'transparent',
                  border: isSelected ? `1px solid ${color}60` : '1px solid transparent',
                  transform: isHovered ? 'scale(1.05)' : 'scale(1)',
                  boxShadow: isSelected ? `0 0 12px ${color}40` : 'none',
                  '&:hover': {
                    bgcolor: `${color}15`,
                    border: `1px solid ${color}40`,
                  },
                }}
              >
                <Box
                  sx={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    bgcolor: color,
                    boxShadow: isSelected || isHovered ? `0 0 8px ${color}` : `0 0 6px ${color}60`,
                    transition: 'all 0.2s ease',
                    transform: isSelected ? 'scale(1.2)' : 'scale(1)',
                  }}
                />
                <Typography
                  variant="caption"
                  sx={{
                    fontSize: '0.65rem',
                    textTransform: 'capitalize',
                    fontWeight: isSelected ? 600 : 400,
                    color: isSelected ? '#fff' : 'rgba(255,255,255,0.8)',
                    transition: 'all 0.2s ease',
                  }}
                >
                  {type}
                </Typography>
              </Box>
            );
          })}
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
            top: 100,
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
        <GlassmorphicTooltip title="Zoom In" placement="left" arrow>
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
        </GlassmorphicTooltip>
        <GlassmorphicTooltip title="Zoom Out" placement="left" arrow>
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
        </GlassmorphicTooltip>
        <GlassmorphicTooltip title="Fit to View" placement="left" arrow>
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
        </GlassmorphicTooltip>
        
        {/* Re-Layout Button */}
        <GlassmorphicTooltip title="Re-layout Graph" placement="left" arrow>
          <IconButton
            size="small"
            onClick={handleReLayout}
            sx={{
              bgcolor: 'rgba(0, 0, 0, 0.6)',
              backdropFilter: 'blur(12px)',
              color: 'white',
              mt: 1,
              '&:hover': { 
                bgcolor: 'rgba(0, 0, 0, 0.8)',
                transform: 'rotate(180deg)',
                transition: 'transform 0.6s ease',
              },
              transition: 'transform 0.6s ease',
            }}
          >
            <LayoutIcon fontSize="small" />
          </IconButton>
        </GlassmorphicTooltip>
        
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
          nodeVal={(node: any) => {
            // Always return same size regardless of selection state
            return node.val;
          }}
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
            
            // Determine if node should be highlighted
            const isTypeSelected = selectedNodeTypes.size > 0;
            const isThisTypeSelected = selectedNodeTypes.has(node.type);
            const isThisTypeHovered = hoveredLegendType === node.type;
            const shouldHighlight = isThisTypeSelected || isThisTypeHovered;
            const shouldFade = isTypeSelected && !shouldHighlight;
            
            // Draw prominent ring for highlighted nodes
            if (shouldHighlight) {
              // Outer glow ring
              ctx.beginPath();
              ctx.arc(node.x, node.y, nodeRadius + 12, 0, 2 * Math.PI);
              const gradient = ctx.createRadialGradient(node.x, node.y, nodeRadius + 8, node.x, node.y, nodeRadius + 12);
              gradient.addColorStop(0, `${node.color}80`);
              gradient.addColorStop(1, 'transparent');
              ctx.fillStyle = gradient;
              ctx.fill();
              
              // Prominent selection ring - thicker and more visible
              ctx.beginPath();
              ctx.arc(node.x, node.y, nodeRadius + 6, 0, 2 * Math.PI);
              ctx.strokeStyle = node.color;
              ctx.lineWidth = 4 / globalScale;
              ctx.globalAlpha = 1;
              ctx.stroke();
              ctx.globalAlpha = 1;
              
              // Inner white ring for extra emphasis
              ctx.beginPath();
              ctx.arc(node.x, node.y, nodeRadius + 4, 0, 2 * Math.PI);
              ctx.strokeStyle = '#ffffff';
              ctx.lineWidth = 2 / globalScale;
              ctx.globalAlpha = 0.8;
              ctx.stroke();
              ctx.globalAlpha = 1;
            } else if (isCurrent && !shouldFade) {
              // Normal glow for non-highlighted current nodes
              ctx.beginPath();
              ctx.arc(node.x, node.y, nodeRadius + 4, 0, 2 * Math.PI);
              const gradient = ctx.createRadialGradient(node.x, node.y, nodeRadius, node.x, node.y, nodeRadius + 4);
              gradient.addColorStop(0, `${node.color}40`);
              gradient.addColorStop(1, 'transparent');
              ctx.fillStyle = gradient;
              ctx.fill();
            }
            
            // Draw node circle with fade effect (no size change)
            ctx.beginPath();
            ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI);
            ctx.fillStyle = node.color || '#64748B';
            
            if (shouldFade) {
              ctx.globalAlpha = isCurrent ? 0.25 : 0.15;
            } else if (shouldHighlight) {
              ctx.globalAlpha = isCurrent ? 1 : 0.5;
            } else {
              ctx.globalAlpha = isCurrent ? 1 : 0.3;
            }
            
            ctx.fill();
            ctx.globalAlpha = 1;
            
            // Draw border (consistent width)
            ctx.strokeStyle = node.color || '#64748B';
            ctx.lineWidth = 2 / globalScale;
            
            if (shouldFade) {
              ctx.globalAlpha = 0.25;
            } else if (!isCurrent) {
              ctx.setLineDash([5 / globalScale, 3 / globalScale]);
            }
            
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.globalAlpha = 1;
            
            // Draw label with background for better readability
            if (globalScale > 0.8 && !shouldFade) {
              ctx.font = `600 ${fontSize}px Inter, sans-serif`;
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              
              const labelY = node.y + nodeRadius + fontSize + 4;
              const textMetrics = ctx.measureText(label);
              const padding = shouldHighlight ? 8 : 6;
              
              // Draw label background
              ctx.fillStyle = shouldHighlight ? `${node.color}30` : 'rgba(0, 0, 0, 0.75)';
              ctx.fillRect(
                node.x - textMetrics.width / 2 - padding,
                labelY - fontSize / 2 - padding / 2,
                textMetrics.width + padding * 2,
                fontSize + padding
              );
              
              // Draw label text
              if (shouldHighlight) {
                ctx.fillStyle = '#ffffff';
                ctx.shadowColor = node.color;
                ctx.shadowBlur = 4;
              } else {
                ctx.fillStyle = isCurrent ? '#ffffff' : 'rgba(255, 255, 255, 0.6)';
              }
              
              ctx.fillText(label, node.x, labelY);
              ctx.shadowBlur = 0;
            }
          }}
          linkColor={(link: any) => {
            const isCurrent = link.is_current === 1;
            return isCurrent ? 'rgba(148, 163, 184, 0.6)' : 'rgba(148, 163, 184, 0.2)';
          }}
          linkWidth={(link: any) => Math.max(link.strength * 4, 1)}
          linkDirectionalParticles={(link: any) => link.is_current === 1 ? 3 : 0}
          linkDirectionalParticleWidth={3}
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

            {/* Entity Timeline - Temporal History */}
            <Box sx={{ mt: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="caption" sx={{ 
                  color: 'rgba(255,255,255,0.6)', 
                  textTransform: 'uppercase', 
                  fontSize: '0.65rem', 
                  fontWeight: 600,
                  letterSpacing: '0.05em'
                }}>
                  📅 Timeline {nodeHistory && `(${nodeHistory.total_versions} versions)`}
                </Typography>
                {loadingHistory && <CircularProgress size={16} sx={{ color: 'rgba(255,255,255,0.5)' }} />}
              </Box>
                
              <Box sx={{ position: 'relative', pl: 3 }}>
                {/* Timeline line */}
                <Box sx={{
                  position: 'absolute',
                  left: '8px',
                  top: '8px',
                  bottom: '8px',
                  width: '2px',
                  background: 'linear-gradient(180deg, rgba(59, 130, 246, 0.5) 0%, rgba(59, 130, 246, 0.1) 100%)',
                }} />
                
                {/* Show all versions if history loaded */}
                {nodeHistory && nodeHistory.versions.map((version, index) => (
                  <Box key={version.id} sx={{ position: 'relative', mb: 3 }}>
                    {/* Version marker */}
                    <Box sx={{
                      position: 'absolute',
                      left: '-19px',
                      top: '4px',
                      width: '12px',
                      height: '12px',
                      borderRadius: '50%',
                      bgcolor: version.is_current === 1 ? '#10B981' : 'transparent',
                      border: version.is_current === 1 
                        ? '2px solid rgba(16, 185, 129, 0.3)' 
                        : '2px solid rgba(148, 163, 184, 0.3)',
                      boxShadow: version.is_current === 1 ? '0 0 12px rgba(16, 185, 129, 0.6)' : 'none',
                    }} />
                    
                    <Paper sx={{
                      p: 2,
                      background: version.is_current === 1
                        ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%)'
                        : 'rgba(255,255,255,0.03)',
                      backdropFilter: 'blur(10px)',
                      border: version.is_current === 1
                        ? '1px solid rgba(16, 185, 129, 0.2)'
                        : '1px solid rgba(255,255,255,0.08)',
                      borderRadius: '10px',
                    }}>
                      <Typography variant="body2" sx={{ 
                        fontWeight: 600, 
                        color: version.is_current === 1 ? '#10B981' : 'rgba(255,255,255,0.7)',
                        mb: 1 
                      }}>
                        {version.is_current === 1 ? 'NOW (Current)' : `Version ${nodeHistory.total_versions - index}`}
                      </Typography>
                      
                      {/* Property changes diff */}
                      {index < nodeHistory.versions.length - 1 && (() => {
                        const prevVersion = nodeHistory.versions[index + 1];
                        const changedProps: string[] = [];
                        Object.keys(version.properties).forEach(key => {
                          if (JSON.stringify(version.properties[key]) !== JSON.stringify(prevVersion.properties[key])) {
                            changedProps.push(key);
                          }
                        });
                        return changedProps.length > 0 && (
                          <Box sx={{ mb: 1 }}>
                            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', display: 'block', mb: 0.5 }}>
                              Changed: {changedProps.join(', ')}
                            </Typography>
                            {changedProps.map(key => (
                              <Typography key={key} variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', display: 'block', fontSize: '0.65rem' }}>
                                {key}: {JSON.stringify(prevVersion.properties[key])} → {JSON.stringify(version.properties[key])}
                              </Typography>
                            ))}
                          </Box>
                        );
                      })()}
                      
                      {/* Reason for change */}
                      {version.reason && (
                        <Chip 
                          label={version.reason.replace(/_/g, ' ')}
                          size="small"
                          sx={{
                            height: '20px',
                            fontSize: '0.65rem',
                            bgcolor: 'rgba(59, 130, 246, 0.15)',
                            color: '#3B82F6',
                            border: '1px solid rgba(59, 130, 246, 0.3)',
                            mb: 1
                          }}
                        />
                      )}
                      
                      {/* Timestamps */}
                      <Box sx={{ mb: 1 }}>
                        {version.valid_from ? (
                          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', display: 'block' }}>
                            {version.valid_until 
                              ? `⏱️ Valid: ${new Date(version.valid_from).toLocaleDateString()} → ${new Date(version.valid_until).toLocaleDateString()}`
                              : `⏱️ Valid since: ${new Date(version.valid_from).toLocaleDateString()}`
                            }
                          </Typography>
                        ) : (
                          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', display: 'block' }}>
                            📅 Created: {new Date(version.created_at).toLocaleDateString()}
                          </Typography>
                        )}
                        {version.updated_at && version.updated_at !== version.created_at && (
                          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', display: 'block', fontSize: '0.6rem' }}>
                            Updated: {new Date(version.updated_at).toLocaleDateString()}
                          </Typography>
                        )}
                      </Box>
                      
                      {version.source_text && nodeHistory.total_versions > 1 && (
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="caption" sx={{ 
                            color: 'rgba(255,255,255,0.5)', 
                            display: 'block',
                            fontSize: '0.6rem',
                            fontWeight: 600,
                            mb: 0.5
                          }}>
                            📄 Source Context:
                          </Typography>
                          <Typography variant="caption" sx={{ 
                            color: 'rgba(255,255,255,0.4)', 
                            display: 'block',
                            fontStyle: 'italic',
                            fontSize: '0.65rem'
                          }}>
                            "{version.source_text.substring(0, 100)}{version.source_text.length > 100 ? '...' : ''}"
                          </Typography>
                        </Box>
                      )}
                    </Paper>
                  </Box>
                ))}
              </Box>
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

      {/* Floating VCR-style Temporal Controls */}
      <TemporalControls
        onTimeChange={handleTimelineChange}
        activityData={activityData}
      />
    </Box>
  );
};
