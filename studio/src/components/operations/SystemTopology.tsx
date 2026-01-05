import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, Chip, CircularProgress, Alert } from '@mui/material';
import { DetailDrawer } from '../common/DetailDrawer';
import {
  CheckCircle as HealthyIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Computer as BackendIcon,
  Memory as ModelIcon,
  Schedule as SchedulerIcon,
  Dashboard as StudioIcon,
  Storage as DatabaseIcon,
  Hub as BusIcon,
  Router as GatewayIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { fetchTopologyData } from '../../api/operations';

interface ServiceNode {
  id: string;
  name: string;
  type: string;
  status: 'healthy' | 'degraded' | 'critical' | 'offline';
  version: string;
  host: string;
  port?: number;
  uptime: string;
}

interface ServiceConnection {
  from: string;
  to: string;
  protocol: string;
  port?: number;
  status: 'active' | 'inactive';
  latency?: number;
}

interface TopologyData {
  services: ServiceNode[];
  connections: ServiceConnection[];
  deployment_type: string;
}

interface SystemTopologyProps {
  refreshTrigger?: number;
}

export const SystemTopology: React.FC<SystemTopologyProps> = ({ refreshTrigger }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [topologyData, setTopologyData] = useState<TopologyData | null>(null);
  const [selectedNode, setSelectedNode] = useState<ServiceNode | null>(null);
  const [zoom, setZoom] = useState(1);
  const initialLoadComplete = React.useRef(false);

  useEffect(() => {
    loadTopologyData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (refreshTrigger !== undefined && refreshTrigger > 0 && initialLoadComplete.current) {
      loadTopologyData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshTrigger]);

  const loadTopologyData = async () => {
    try {
      // Only show loading spinner on initial load, not on refresh
      if (!initialLoadComplete.current) {
        setLoading(true);
      }
      setError(null);
      const data = await fetchTopologyData();
      setTopologyData(data);
      if (!initialLoadComplete.current) {
        initialLoadComplete.current = true;
        setLoading(false);
      }
    } catch (err: any) {
      console.error('Failed to load topology data:', err);
      setError(err.message || 'Failed to load topology data');
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return '#10B981';
      case 'degraded': return '#F59E0B';
      case 'critical': return '#EF4444';
      case 'offline': return '#6B7280';
      default: return '#6B7280';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <HealthyIcon sx={{ fontSize: 16 }} />;
      case 'degraded': return <WarningIcon sx={{ fontSize: 16 }} />;
      case 'critical': return <ErrorIcon sx={{ fontSize: 16 }} />;
      default: return <ErrorIcon sx={{ fontSize: 16 }} />;
    }
  };

  const getServiceIcon = (type: string) => {
    switch (type) {
      case 'backend': return <BackendIcon />;
      case 'modelservice': return <ModelIcon />;
      case 'scheduler': return <SchedulerIcon />;
      case 'studio': return <StudioIcon />;
      case 'database': return <DatabaseIcon />;
      case 'bus': return <BusIcon />;
      case 'gateway': return <GatewayIcon />;
      default: return <BackendIcon />;
    }
  };

  const handleNodeClick = (node: ServiceNode) => {
    setSelectedNode(node);
  };

  const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.2, 2));
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 0.2, 0.5));
  const handleResetZoom = () => setZoom(1);

  // Helper functions for network diagram
  const getProtocolColor = (protocol: string): string => {
    if (protocol.includes('HTTP')) return '#6366F1';
    if (protocol.includes('WebSocket')) return '#10B981';
    if (protocol.includes('ZMQ')) return '#F59E0B';
    if (protocol.includes('SQLite') || protocol.includes('Direct')) return '#8B5CF6';
    return '#6B7280';
  };

  const getProtocolMarker = (protocol: string): string => {
    if (protocol.includes('HTTP')) return 'arrowHTTP';
    if (protocol.includes('WebSocket')) return 'arrowWS';
    if (protocol.includes('ZMQ')) return 'arrowZMQ';
    return 'arrowOther';
  };

  const getServicePosition = (service: ServiceNode, allServices: ServiceNode[]): { x: number; y: number } => {
    // Layout services to minimize line crossings and overlaps
    const width = 1000;
    const height = 700;
    const padding = 80;
    
    // Presentation layer (top) - spread horizontally
    if (['studio', 'Studio'].includes(service.id) || service.name === 'Studio') {
      return { x: width * 0.2, y: padding + 40 };
    }
    if (service.name === 'Frontend') {
      return { x: width * 0.5, y: padding + 40 };
    }
    if (service.name === 'CLI') {
      return { x: width * 0.8, y: padding + 40 };
    }
    
    // Gateway layer - centered
    if (service.type === 'gateway') {
      return { x: width * 0.5, y: padding + 160 };
    }
    
    // Backend layer - centered
    if (service.type === 'backend') {
      return { x: width * 0.5, y: padding + 280 };
    }
    
    // Application services layer - spread horizontally at same level as backend
    // This prevents diagonal lines through nodes
    if (service.type === 'modelservice') {
      return { x: width * 0.15, y: padding + 280 }; // Same Y as backend, to the left
    }
    if (service.type === 'scheduler') {
      return { x: width * 0.35, y: padding + 400 }; // Below and between
    }
    if (service.type === 'bus') {
      return { x: width * 0.65, y: padding + 400 }; // Below and to the right
    }
    
    // Data layer (bottom) - aligned with their parent services
    if (service.name === 'LibSQL') {
      return { x: width * 0.15, y: padding + 540 }; // Below Model Service
    }
    if (service.name === 'ChromaDB') {
      return { x: width * 0.5, y: padding + 540 }; // Below Backend
    }
    if (service.name === 'LMDB') {
      return { x: width * 0.85, y: padding + 540 }; // Far right
    }
    
    // Default fallback
    return { x: width * 0.5, y: height * 0.5 };
  };

  // Network Node Component for network diagram
  const NetworkNode: React.FC<{
    service: ServiceNode;
    connections: ServiceConnection[];
    onClick: (service: ServiceNode) => void;
  }> = ({ service, connections, onClick }) => {
    const outgoingCount = connections.filter(c => 
      c.from === service.id || c.from.toLowerCase() === service.name.toLowerCase()
    ).length;
    const incomingCount = connections.filter(c => 
      c.to === service.id || c.to.toLowerCase() === service.name.toLowerCase()
    ).length;

    return (
      <Paper
        onClick={() => onClick(service)}
        sx={{
          p: 1.5,
          borderRadius: '10px',
          border: '1px solid',
          borderColor: 'rgba(184, 161, 234, 0.3)',
          background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.03) 0%, rgba(99, 102, 241, 0.05) 100%)',
          backdropFilter: 'blur(8px)',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          '&:hover': {
            transform: 'translateX(4px)',
            borderColor: '#B8A1EA',
            background: 'linear-gradient(135deg, rgba(184, 161, 234, 0.1) 0%, rgba(99, 102, 241, 0.08) 100%)',
          },
        }}
      >
        <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.75rem', mb: 0.5 }}>
          {service.name}
        </Typography>
        <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
          {incomingCount > 0 && (
            <Chip
              label={`← ${incomingCount}`}
              size="small"
              sx={{
                height: 16,
                fontSize: '0.6rem',
                bgcolor: 'rgba(16, 185, 129, 0.15)',
                color: '#10B981',
              }}
            />
          )}
          {outgoingCount > 0 && (
            <Chip
              label={`${outgoingCount} →`}
              size="small"
              sx={{
                height: 16,
                fontSize: '0.6rem',
                bgcolor: 'rgba(99, 102, 241, 0.15)',
                color: '#6366F1',
              }}
            />
          )}
        </Box>
      </Paper>
    );
  };

  // Service Node Component for rendering individual services
  const ServiceNodeComponent: React.FC<{
    service: ServiceNode;
    selected: boolean;
    onClick: (service: ServiceNode) => void;
    getStatusColor: (status: string) => string;
    getStatusIcon: (status: string) => React.ReactNode;
    getServiceIcon: (type: string) => React.ReactNode;
  }> = ({ service, selected, onClick, getStatusColor, getStatusIcon, getServiceIcon }) => (
    <Paper
      onClick={() => onClick(service)}
      sx={{
        p: 2,
        borderRadius: '12px',
        border: selected ? '2px solid' : '1.5px solid',
        borderColor: selected ? '#B8A1EA' : `${getStatusColor(service.status)}60`,
        background: selected
          ? 'linear-gradient(135deg, rgba(184, 161, 234, 0.2) 0%, rgba(99, 102, 241, 0.1) 100%)'
          : 'linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(99, 102, 241, 0.08) 100%)',
        backdropFilter: 'blur(8px)',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        minWidth: 140,
        '&:hover': {
          transform: 'translateY(-2px)',
          borderColor: '#B8A1EA',
          boxShadow: '0 4px 12px rgba(184, 161, 234, 0.3)',
        },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
        <Box
          sx={{
            width: 32,
            height: 32,
            borderRadius: '8px',
            bgcolor: 'rgba(184, 161, 234, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#B8A1EA',
          }}
        >
          {getServiceIcon(service.type)}
        </Box>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.8rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {service.name}
          </Typography>
        </Box>
        <Box sx={{ color: getStatusColor(service.status), fontSize: 16 }}>
          {getStatusIcon(service.status)}
        </Box>
      </Box>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary', fontFamily: 'monospace' }}>
          {service.host}{service.port ? `:${service.port}` : ''}
        </Typography>
        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
          <Chip
            label={service.version}
            size="small"
            sx={{
              height: 18,
              fontSize: '0.6rem',
              bgcolor: 'rgba(99, 102, 241, 0.15)',
              color: '#6366F1',
            }}
          />
          <Chip
            label={service.uptime}
            size="small"
            sx={{
              height: 18,
              fontSize: '0.6rem',
              bgcolor: 'rgba(255, 255, 255, 0.05)',
              color: 'text.secondary',
            }}
          />
        </Box>
      </Box>
    </Paper>
  );

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress sx={{ color: '#B8A1EA' }} />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!topologyData) {
    return (
      <Alert severity="info" sx={{ mb: 2 }}>
        No topology data available
      </Alert>
    );
  }

  return (
    <Box>
      {/* Architecture Diagram */}
      <Paper
        sx={{
          p: 3,
          borderRadius: '16px',
          border: '1.5px solid',
          borderColor: 'divider',
          background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, rgba(99, 102, 241, 0.05) 100%)',
          backdropFilter: 'blur(8px)',
          mb: 3,
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '0.85rem' }}>
            System Architecture
          </Typography>
          <Chip
            label={`Deployment: ${topologyData.deployment_type}`}
            size="small"
            sx={{
              height: 22,
              fontSize: '0.65rem',
              bgcolor: 'rgba(184, 161, 234, 0.15)',
              color: '#B8A1EA',
              fontWeight: 600,
            }}
          />
        </Box>

        {/* Layered Architecture Visualization */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          
          {/* Layer 1: Frontend */}
          <Box>
            <Typography variant="caption" sx={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'text.secondary', mb: 1, display: 'block' }}>
              Presentation Layer
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
              {/* Studio (Web) */}
              {topologyData.services.filter(s => s.type === 'studio').map(service => (
                <ServiceNodeComponent key={service.id} service={service} selected={selectedNode?.id === service.id} onClick={handleNodeClick} getStatusColor={getStatusColor} getStatusIcon={getStatusIcon} getServiceIcon={getServiceIcon} />
              ))}
              
              {/* Flutter Frontend (Non-interactive) */}
              <Paper
                sx={{
                  p: 2,
                  borderRadius: '12px',
                  border: '1.5px dashed',
                  borderColor: 'rgba(184, 161, 234, 0.4)',
                  background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, rgba(99, 102, 241, 0.03) 100%)',
                  backdropFilter: 'blur(8px)',
                  minWidth: 140,
                  opacity: 0.7,
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
                  <Box
                    sx={{
                      width: 32,
                      height: 32,
                      borderRadius: '8px',
                      bgcolor: 'rgba(184, 161, 234, 0.15)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#B8A1EA',
                    }}
                  >
                    <StudioIcon />
                  </Box>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.8rem' }}>
                      Frontend
                    </Typography>
                  </Box>
                </Box>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                  <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary', fontFamily: 'monospace' }}>
                    Flutter App
                  </Typography>
                  <Chip
                    label="External"
                    size="small"
                    sx={{
                      height: 18,
                      fontSize: '0.6rem',
                      bgcolor: 'rgba(107, 114, 128, 0.15)',
                      color: 'text.secondary',
                    }}
                  />
                </Box>
              </Paper>

              {/* CLI (Non-interactive) */}
              <Paper
                sx={{
                  p: 2,
                  borderRadius: '12px',
                  border: '1.5px dashed',
                  borderColor: 'rgba(184, 161, 234, 0.4)',
                  background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, rgba(99, 102, 241, 0.03) 100%)',
                  backdropFilter: 'blur(8px)',
                  minWidth: 140,
                  opacity: 0.7,
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
                  <Box
                    sx={{
                      width: 32,
                      height: 32,
                      borderRadius: '8px',
                      bgcolor: 'rgba(184, 161, 234, 0.15)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#B8A1EA',
                    }}
                  >
                    <BackendIcon />
                  </Box>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.8rem' }}>
                      CLI
                    </Typography>
                  </Box>
                </Box>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                  <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary', fontFamily: 'monospace' }}>
                    Command Line
                  </Typography>
                  <Chip
                    label="External"
                    size="small"
                    sx={{
                      height: 18,
                      fontSize: '0.6rem',
                      bgcolor: 'rgba(107, 114, 128, 0.15)',
                      color: 'text.secondary',
                    }}
                  />
                </Box>
              </Paper>
            </Box>
            {/* Connection Arrow */}
            <Box sx={{ display: 'flex', justifyContent: 'center', my: 1 }}>
              <Typography sx={{ color: '#6366F1', fontSize: '1.5rem' }}>↓</Typography>
            </Box>
          </Box>

          {/* Layer 2: API Gateway */}
          <Box>
            <Typography variant="caption" sx={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'text.secondary', mb: 1, display: 'block' }}>
              Gateway Layer
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
              {topologyData.services.filter(s => s.type === 'gateway').map(service => (
                <ServiceNodeComponent key={service.id} service={service} selected={selectedNode?.id === service.id} onClick={handleNodeClick} getStatusColor={getStatusColor} getStatusIcon={getStatusIcon} getServiceIcon={getServiceIcon} />
              ))}
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'center', my: 1 }}>
              <Typography sx={{ color: '#6366F1', fontSize: '1.5rem' }}>↓</Typography>
            </Box>
          </Box>

          {/* Layer 3: Backend & Services */}
          <Box>
            <Typography variant="caption" sx={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'text.secondary', mb: 1, display: 'block' }}>
              Application Layer
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
              {topologyData.services.filter(s => ['backend', 'modelservice', 'scheduler', 'bus', 'ollama'].includes(s.type)).map(service => (
                <ServiceNodeComponent key={service.id} service={service} selected={selectedNode?.id === service.id} onClick={handleNodeClick} getStatusColor={getStatusColor} getStatusIcon={getStatusIcon} getServiceIcon={getServiceIcon} />
              ))}
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'center', my: 1 }}>
              <Typography sx={{ color: '#6366F1', fontSize: '1.5rem' }}>↓</Typography>
            </Box>
          </Box>

          {/* Layer 4: Data Layer */}
          <Box>
            <Typography variant="caption" sx={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'text.secondary', mb: 1, display: 'block' }}>
              Data Layer
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
              {topologyData.services.filter(s => s.type === 'database').map(service => (
                <ServiceNodeComponent key={service.id} service={service} selected={selectedNode?.id === service.id} onClick={handleNodeClick} getStatusColor={getStatusColor} getStatusIcon={getStatusIcon} getServiceIcon={getServiceIcon} />
              ))}
            </Box>
          </Box>
        </Box>
      </Paper>


      {/* Right-side Detail Drawer */}
      <DetailDrawer
        open={!!selectedNode}
        onClose={() => setSelectedNode(null)}
        title="Service Details"
        width={400}
      >
        {selectedNode && (
          <Box>
            {/* Service Icon and Name */}
            <Box
              sx={{
                p: 2.5,
                borderRadius: '12px',
                background: 'linear-gradient(135deg, rgba(184, 161, 234, 0.15) 0%, rgba(99, 102, 241, 0.08) 100%)',
                border: '1px solid',
                borderColor: 'rgba(184, 161, 234, 0.3)',
                mb: 3,
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Box
                  sx={{
                    width: 48,
                    height: 48,
                    borderRadius: '12px',
                    bgcolor: 'rgba(184, 161, 234, 0.2)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#B8A1EA',
                    fontSize: 28,
                  }}
                >
                  {getServiceIcon(selectedNode.type)}
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1.1rem', mb: 0.5 }}>
                    {selectedNode.name}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Box sx={{ color: getStatusColor(selectedNode.status), fontSize: 18 }}>
                      {getStatusIcon(selectedNode.status)}
                    </Box>
                    <Typography variant="body2" sx={{ fontWeight: 600, textTransform: 'capitalize', color: getStatusColor(selectedNode.status) }}>
                      {selectedNode.status}
                    </Typography>
                  </Box>
                </Box>
              </Box>
            </Box>

            {/* Details Grid */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
              <Box>
                <Typography variant="caption" sx={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'text.secondary', mb: 1, display: 'block' }}>
                  Type
                </Typography>
                <Chip
                  label={selectedNode.type}
                  size="small"
                  sx={{
                    height: 24,
                    fontSize: '0.75rem',
                    bgcolor: 'rgba(99, 102, 241, 0.15)',
                    color: '#6366F1',
                    fontWeight: 600,
                  }}
                />
              </Box>

              <Box>
                <Typography variant="caption" sx={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'text.secondary', mb: 1, display: 'block' }}>
                  Version
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 600, fontSize: '0.95rem' }}>
                  {selectedNode.version}
                </Typography>
              </Box>

              <Box>
                <Typography variant="caption" sx={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'text.secondary', mb: 1, display: 'block' }}>
                  Location
                </Typography>
                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: '8px',
                    bgcolor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid',
                    borderColor: 'rgba(255, 255, 255, 0.05)',
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'monospace', fontSize: '0.85rem', color: '#B8A1EA' }}>
                    {selectedNode.host}{selectedNode.port ? `:${selectedNode.port}` : ''}
                  </Typography>
                </Box>
              </Box>

              <Box>
                <Typography variant="caption" sx={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'text.secondary', mb: 1, display: 'block' }}>
                  Uptime
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 600, fontSize: '0.95rem' }}>
                  {selectedNode.uptime}
                </Typography>
              </Box>

              {/* Connection Info */}
              <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'rgba(255, 255, 255, 0.05)' }}>
                <Typography variant="caption" sx={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'text.secondary', mb: 1.5, display: 'block' }}>
                  Connections
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {topologyData.connections
                    .filter(conn => 
                      conn.from === selectedNode.id || 
                      conn.to === selectedNode.id ||
                      conn.from.toLowerCase() === selectedNode.name.toLowerCase() ||
                      conn.to.toLowerCase() === selectedNode.name.toLowerCase()
                    )
                    .map((conn, idx) => (
                      <Box
                        key={idx}
                        sx={{
                          p: 1.5,
                          borderRadius: '8px',
                          bgcolor: 'rgba(255, 255, 255, 0.03)',
                          border: '1px solid',
                          borderColor: 'rgba(255, 255, 255, 0.05)',
                        }}
                      >
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', mb: 0.5 }}>
                          {conn.from === selectedNode.id ? '→ ' : '← '}
                          <strong>{conn.from === selectedNode.id ? conn.to : conn.from}</strong>
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                          <Chip
                            label={conn.protocol}
                            size="small"
                            sx={{
                              height: 18,
                              fontSize: '0.6rem',
                              bgcolor: 'rgba(99, 102, 241, 0.15)',
                              color: '#6366F1',
                            }}
                          />
                          {conn.port && (
                            <Chip
                              label={`:${conn.port}`}
                              size="small"
                              sx={{
                                height: 18,
                                fontSize: '0.6rem',
                                bgcolor: 'rgba(255, 255, 255, 0.05)',
                                color: 'text.secondary',
                              }}
                            />
                          )}
                        </Box>
                      </Box>
                    ))}
                </Box>
              </Box>
            </Box>
          </Box>
        )}
      </DetailDrawer>
    </Box>
  );
};
