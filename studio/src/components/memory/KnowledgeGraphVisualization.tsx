import React, { useEffect, useRef, useState } from 'react';
import { Box, Typography, Chip, IconButton, Tooltip, Paper } from '@mui/material';
import {
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  CenterFocusStrong as CenterIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';

interface GraphNode {
  id: string;
  label: string;
  type: 'person' | 'organization' | 'location' | 'event' | 'project' | 'goal' | 'task' | 'activity' | 'interest' | 'priority' | 'skill' | 'topic' | 'product';
  connections: number;
  importance: number;
  properties?: {
    status?: string;
    progress?: number;
    is_current?: boolean;
  };
}

interface GraphEdge {
  source: string;
  target: string;
  relation_type: 'WORKS_FOR' | 'WORKS_AT' | 'LIVES_IN' | 'KNOWS' | 'WORKING_ON' | 'HAS_GOAL' | 'DEPENDS_ON' | 'CONTRIBUTES_TO' | 'INTERESTED_IN' | 'PRIORITIZES' | 'COMPLETED' | 'STARTED' | 'PART_OF' | 'HAPPENED_IN' | 'LOCATED_IN';
  strength: number;
  properties?: Record<string, any>;
}

interface KnowledgeGraphVisualizationProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (node: GraphNode) => void;
}

const nodeColors = {
  // World Knowledge Graph
  person: '#8B5CF6',
  organization: '#6366F1',
  location: '#F59E0B',
  event: '#10B981',
  product: '#06B6D4',
  skill: '#EC4899',
  topic: '#3B82F6',
  // Personal Graph
  project: '#8B5CF6',
  goal: '#10B981',
  task: '#3B82F6',
  activity: '#F59E0B',
  interest: '#EC4899',
  priority: '#EF4444',
};

export const KnowledgeGraphVisualization: React.FC<KnowledgeGraphVisualizationProps> = ({
  nodes,
  edges,
  onNodeClick,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Simple force-directed layout simulation
  const [nodePositions, setNodePositions] = useState<Map<string, { x: number; y: number }>>(new Map());

  useEffect(() => {
    if (!canvasRef.current || nodes.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Initialize positions if not set
    if (nodePositions.size === 0) {
      const positions = new Map<string, { x: number; y: number }>();
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const radius = Math.min(canvas.width, canvas.height) * 0.3;

      nodes.forEach((node, i) => {
        const angle = (i / nodes.length) * 2 * Math.PI;
        positions.set(node.id, {
          x: centerX + radius * Math.cos(angle),
          y: centerY + radius * Math.sin(angle),
        });
      });
      setNodePositions(positions);
    }

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();

    // Apply zoom and offset
    ctx.translate(offset.x, offset.y);
    ctx.scale(zoom, zoom);

    // Draw edges
    edges.forEach((edge) => {
      const sourcePos = nodePositions.get(edge.source);
      const targetPos = nodePositions.get(edge.target);
      if (!sourcePos || !targetPos) return;

      // Draw edge line
      ctx.beginPath();
      ctx.moveTo(sourcePos.x, sourcePos.y);
      ctx.lineTo(targetPos.x, targetPos.y);
      ctx.strokeStyle = `rgba(148, 163, 184, ${edge.strength * 0.5})`;
      ctx.lineWidth = edge.strength * 2;
      ctx.stroke();

      // Draw edge label (relationship type)
      const midX = (sourcePos.x + targetPos.x) / 2;
      const midY = (sourcePos.y + targetPos.y) / 2;
      ctx.fillStyle = 'rgba(148, 163, 184, 0.8)';
      ctx.font = '10px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(edge.relation_type, midX, midY - 5);
    });

    // Draw nodes
    nodes.forEach((node) => {
      const pos = nodePositions.get(node.id);
      if (!pos) return;

      const radius = 8 + node.importance * 12;
      const color = nodeColors[node.type];

      // Node circle
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = color + '40';
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.stroke();

      // Inner circle
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius * 0.5, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      // Label
      ctx.fillStyle = '#fff';
      ctx.font = '12px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(node.label, pos.x, pos.y + radius + 16);
    });

    ctx.restore();
  }, [nodes, edges, nodePositions, zoom, offset]);

  const handleZoomIn = () => setZoom((z) => Math.min(z * 1.2, 3));
  const handleZoomOut = () => setZoom((z) => Math.max(z / 1.2, 0.3));
  const handleCenter = () => {
    setZoom(1);
    setOffset({ x: 0, y: 0 });
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDragging) return;
    setOffset({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  return (
    <Box sx={{ position: 'relative' }}>
      {/* Controls */}
      <Box
        sx={{
          position: 'absolute',
          top: 16,
          right: 16,
          display: 'flex',
          gap: 1,
          zIndex: 10,
        }}
      >
        <Tooltip title="Zoom In">
          <IconButton
            size="small"
            onClick={handleZoomIn}
            sx={{
              bgcolor: 'background.paper',
              border: '1px solid',
              borderColor: 'divider',
              '&:hover': { bgcolor: 'action.hover' },
            }}
          >
            <ZoomInIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Zoom Out">
          <IconButton
            size="small"
            onClick={handleZoomOut}
            sx={{
              bgcolor: 'background.paper',
              border: '1px solid',
              borderColor: 'divider',
              '&:hover': { bgcolor: 'action.hover' },
            }}
          >
            <ZoomOutIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Center">
          <IconButton
            size="small"
            onClick={handleCenter}
            sx={{
              bgcolor: 'background.paper',
              border: '1px solid',
              borderColor: 'divider',
              '&:hover': { bgcolor: 'action.hover' },
            }}
          >
            <CenterIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Legend */}
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
        }}
      >
        <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600, mb: 1, display: 'block' }}>
          NODE TYPES
        </Typography>
        <Box sx={{ mb: 1 }}>
          <Typography variant="caption" sx={{ fontSize: '0.65rem', fontWeight: 600, color: 'rgba(255,255,255,0.6)' }}>
            World Knowledge
          </Typography>
          {['person', 'organization', 'location', 'event', 'skill', 'topic'].map((type) => (
            <Box key={type} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5, ml: 1 }}>
              <Box
                sx={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  bgcolor: nodeColors[type as keyof typeof nodeColors],
                  boxShadow: `0 0 6px ${nodeColors[type as keyof typeof nodeColors]}60`,
                }}
              />
              <Typography variant="caption" sx={{ fontSize: '0.65rem', textTransform: 'capitalize' }}>
                {type}
              </Typography>
            </Box>
          ))}
        </Box>
        <Box>
          <Typography variant="caption" sx={{ fontSize: '0.65rem', fontWeight: 600, color: 'rgba(255,255,255,0.6)' }}>
            Personal Graph
          </Typography>
          {['project', 'goal', 'task', 'activity', 'interest', 'priority'].map((type) => (
            <Box key={type} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5, ml: 1 }}>
              <Box
                sx={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  bgcolor: nodeColors[type as keyof typeof nodeColors],
                  boxShadow: `0 0 6px ${nodeColors[type as keyof typeof nodeColors]}60`,
                }}
              />
              <Typography variant="caption" sx={{ fontSize: '0.65rem', textTransform: 'capitalize' }}>
                {type}
              </Typography>
            </Box>
          ))}
        </Box>
      </Paper>

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        width={1200}
        height={600}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{
          width: '100%',
          height: '600px',
          borderRadius: '20px',
          cursor: isDragging ? 'grabbing' : 'grab',
          backgroundColor: 'rgba(0, 0, 0, 0.2)',
        }}
      />

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
    </Box>
  );
};
