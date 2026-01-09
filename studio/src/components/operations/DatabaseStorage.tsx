import React, { useState, useEffect, useMemo } from 'react';
import { Box, Typography, Paper, Chip, Alert, CircularProgress, LinearProgress, Collapse, IconButton, Divider } from '@mui/material';
import { Database, HardDrive, AlertCircle, CheckCircle, AlertTriangle, ChevronDown, ChevronUp, Table, FileText, Key, Layers, List, Hash, Code, Search as SearchIcon } from 'lucide-react';
import { fetchDatabaseStats, DatabaseMetrics, fetchDatabaseDetails, DatabaseDetailsResponse, TableInfo, CollectionInfo, LMDBDatabaseInfo } from '../../api/operations';
import { SQLQueryInterface } from './SQLQueryInterface';
import { LMDBBrowser } from './LMDBBrowser';
import { ChromaDBBrowser } from './ChromaDBBrowser';
import { ChromaDBCollectionBrowser } from './ChromaDBCollectionBrowser';

interface DatabaseStorageProps {
  refreshTrigger?: number;
}

// Database type configuration for consistent styling
const DB_CONFIG = {
  libsql: {
    name: 'LibSQL',
    color: '#3B82F6',
    icon: Database,
    description: 'Primary relational database for system data',
  },
  chromadb: {
    name: 'ChromaDB',
    color: '#8B5CF6',
    icon: Layers,
    description: 'Vector database for semantic memory and embeddings',
  },
  lmdb: {
    name: 'LMDB',
    color: '#14B8A6',
    icon: Key,
    description: 'Key-value store for working memory',
  },
};

const STATUS_CONFIG = {
  healthy: {
    color: '#10B981',
    icon: CheckCircle,
    label: 'Healthy',
  },
  degraded: {
    color: '#F59E0B',
    icon: AlertTriangle,
    label: 'Degraded',
  },
  critical: {
    color: '#EF4444',
    icon: AlertCircle,
    label: 'Critical',
  },
};

export const DatabaseStorage: React.FC<DatabaseStorageProps> = ({ refreshTrigger }) => {
  const [databases, setDatabases] = useState<DatabaseMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedDb, setExpandedDb] = useState<string | null>(null);
  const [databaseDetails, setDatabaseDetails] = useState<Record<string, DatabaseDetailsResponse>>({});
  const [loadingDetails, setLoadingDetails] = useState<Record<string, boolean>>({});
  const [showSQLInterface, setShowSQLInterface] = useState<Record<string, boolean>>({});
  const [showLMDBBrowser, setShowLMDBBrowser] = useState<Record<string, boolean>>({});
  const [showChromaDBBrowser, setShowChromaDBBrowser] = useState<Record<string, boolean>>({});
  const [selectedChromaCollection, setSelectedChromaCollection] = useState<Record<string, string>>({});

  useEffect(() => {
    loadDatabaseStats();
  }, [refreshTrigger]);

  const loadDatabaseStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetchDatabaseStats();
      setDatabases(response.databases);
    } catch (err: any) {
      console.error('Failed to load database stats:', err);
      setError(err.message || 'Failed to load database statistics');
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  const formatNumber = (num: number | null | undefined): string => {
    if (num === null || num === undefined) return '0';
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  // Calculate total storage metrics
  const totalMetrics = useMemo(() => {
    const total = databases.reduce((sum, db) => sum + db.size_bytes, 0);
    const healthyCount = databases.filter(db => db.status === 'healthy').length;
    const degradedCount = databases.filter(db => db.status === 'degraded').length;
    const criticalCount = databases.filter(db => db.status === 'critical').length;

    return {
      totalSize: total,
      healthyCount,
      degradedCount,
      criticalCount,
      overallStatus: (criticalCount > 0 ? 'critical' : degradedCount > 0 ? 'degraded' : 'healthy') as 'healthy' | 'degraded' | 'critical',
    };
  }, [databases]);

  const toggleExpanded = async (dbName: string, dbType: string) => {
    const isExpanding = expandedDb !== dbName;
    setExpandedDb(isExpanding ? dbName : null);
    
    // Load database details when expanding if not already loaded
    if (isExpanding && !databaseDetails[dbName]) {
      setLoadingDetails(prev => ({ ...prev, [dbName]: true }));
      try {
        const details = await fetchDatabaseDetails(dbType);
        setDatabaseDetails(prev => ({ ...prev, [dbName]: details }));
      } catch (err: any) {
        console.error(`Failed to load details for ${dbName}:`, err);
      } finally {
        setLoadingDetails(prev => ({ ...prev, [dbName]: false }));
      }
    }
  };

  const renderDatabaseMetrics = (db: DatabaseMetrics) => {
    const metrics: { label: string; value: string | number }[] = [];

    // Type-specific metrics
    if (db.type === 'libsql') {
      if (db.table_count !== undefined) metrics.push({ label: 'Tables', value: db.table_count });
      if (db.connection_count !== undefined) metrics.push({ label: 'Connections', value: db.connection_count });
      if (db.wal_size_bytes !== undefined) metrics.push({ label: 'WAL Size', value: formatBytes(db.wal_size_bytes) });
    } else if (db.type === 'chromadb') {
      if (db.collection_count !== undefined) metrics.push({ label: 'Collections', value: db.collection_count });
      if (db.document_count !== undefined) metrics.push({ label: 'Documents', value: formatNumber(db.document_count) });
      if (db.index_size_bytes !== undefined) metrics.push({ label: 'Index Size', value: formatBytes(db.index_size_bytes) });
    } else if (db.type === 'lmdb') {
      if (db.database_count !== undefined) metrics.push({ label: 'Databases', value: db.database_count });
      if (db.key_count !== undefined) metrics.push({ label: 'Keys', value: formatNumber(db.key_count) });
      if (db.map_size_bytes !== undefined) metrics.push({ label: 'Map Size', value: formatBytes(db.map_size_bytes) });
    }

    return metrics;
  };

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      {/* Storage Summary */}
      <Paper
        sx={{
          p: 3,
          mb: 3,
          borderRadius: '16px',
          bgcolor: 'rgba(255, 255, 255, 0.02)',
          backdropFilter: 'blur(12px)',
          border: '1px solid',
          borderColor: 'divider',
          background: `linear-gradient(135deg, rgba(${
            totalMetrics.overallStatus === 'healthy' ? '16, 185, 129' : 
            totalMetrics.overallStatus === 'degraded' ? '245, 158, 11' : 
            '239, 68, 68'
          }, 0.05) 0%, rgba(184, 161, 234, 0.05) 100%)`,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <HardDrive size={24} color={STATUS_CONFIG[totalMetrics.overallStatus].color} />
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            Database & Storage Overview
          </Typography>
        </Box>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' }, gap: 3 }}>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Total Storage
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {formatBytes(totalMetrics.totalSize)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Databases
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {databases.length}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Health Status
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              {totalMetrics.healthyCount > 0 && (
                <Chip
                  label={`${totalMetrics.healthyCount} Healthy`}
                  size="small"
                  sx={{
                    bgcolor: 'rgba(16, 185, 129, 0.15)',
                    color: '#10B981',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    fontSize: '0.7rem',
                    height: 24,
                    fontWeight: 600,
                  }}
                />
              )}
              {totalMetrics.degradedCount > 0 && (
                <Chip
                  label={`${totalMetrics.degradedCount} Degraded`}
                  size="small"
                  sx={{
                    bgcolor: 'rgba(245, 158, 11, 0.15)',
                    color: '#F59E0B',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    fontSize: '0.7rem',
                    height: 24,
                    fontWeight: 600,
                  }}
                />
              )}
              {totalMetrics.criticalCount > 0 && (
                <Chip
                  label={`${totalMetrics.criticalCount} Critical`}
                  size="small"
                  sx={{
                    bgcolor: 'rgba(239, 68, 68, 0.15)',
                    color: '#EF4444',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    fontSize: '0.7rem',
                    height: 24,
                    fontWeight: 600,
                  }}
                />
              )}
            </Box>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Overall Status
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 600, color: STATUS_CONFIG[totalMetrics.overallStatus].color }}>
              {STATUS_CONFIG[totalMetrics.overallStatus].label}
            </Typography>
          </Box>
        </Box>
      </Paper>

      {/* Database Cards */}
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
        Database Details
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {loading && databases.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          databases.map((db) => {
            const config = DB_CONFIG[db.type as keyof typeof DB_CONFIG];
            const statusConfig = STATUS_CONFIG[db.status as 'healthy' | 'degraded' | 'critical'];
            const Icon = config.icon;
            const StatusIcon = statusConfig.icon;
            const isExpanded = expandedDb === db.name;
            const metrics = renderDatabaseMetrics(db);

            return (
              <Paper
                key={db.name}
                sx={{
                  borderRadius: '16px',
                  border: '1.5px solid',
                  borderColor: `${statusConfig.color}40`,
                  background: `linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, ${config.color}08 100%)`,
                  backdropFilter: 'blur(8px)',
                  overflow: 'hidden',
                  transition: 'all 0.2s',
                  '&:hover': {
                    borderColor: statusConfig.color,
                    boxShadow: `0 8px 24px ${statusConfig.color}20`,
                  },
                }}
              >
                {/* Database Header */}
                <Box
                  sx={{
                    p: 2.5,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                  }}
                  onClick={() => toggleExpanded(db.name, db.type)}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flex: 1 }}>
                    <Box
                      sx={{
                        width: 48,
                        height: 48,
                        borderRadius: '12px',
                        bgcolor: `${config.color}15`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <Icon size={24} color={config.color} />
                    </Box>
                    <Box sx={{ flex: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 0.5 }}>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          {config.name}
                        </Typography>
                        <Chip
                          icon={<StatusIcon size={14} />}
                          label={statusConfig.label}
                          size="small"
                          sx={{
                            bgcolor: `${statusConfig.color}15`,
                            color: statusConfig.color,
                            border: '1px solid',
                            borderColor: `${statusConfig.color}30`,
                            fontSize: '0.7rem',
                            height: 24,
                            fontWeight: 600,
                            '& .MuiChip-icon': {
                              color: statusConfig.color,
                            },
                          }}
                        />
                      </Box>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                        {config.description}
                      </Typography>
                      <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.65rem', color: 'text.secondary', display: 'block' }}>
                        {db.location}
                      </Typography>
                    </Box>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                    <Box sx={{ textAlign: 'right' }}>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                        Size
                      </Typography>
                      <Typography variant="h6" sx={{ fontWeight: 600, color: config.color }}>
                        {formatBytes(db.size_bytes)}
                      </Typography>
                    </Box>
                    <IconButton size="small">
                      {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </IconButton>
                  </Box>
                </Box>

                {/* Expanded Details */}
                <Collapse in={isExpanded}>
                  <Box sx={{ px: 2.5, pb: 2.5, pt: 0 }}>
                    {loadingDetails[db.name] ? (
                      <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                        <CircularProgress size={24} />
                      </Box>
                    ) : (
                      <>
                        {/* SQL Query Interface for LibSQL */}
                        {db.type === 'libsql' && (
                          <Box sx={{ mb: 3 }}>
                            <Box
                              sx={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 1,
                                mb: 1.5,
                                cursor: 'pointer',
                                p: 1.5,
                                borderRadius: '8px',
                                bgcolor: showSQLInterface[db.name] ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.05)',
                                border: '1px solid',
                                borderColor: showSQLInterface[db.name] ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.15)',
                                transition: 'all 0.2s',
                                '&:hover': {
                                  bgcolor: 'rgba(59, 130, 246, 0.15)',
                                  borderColor: 'rgba(59, 130, 246, 0.4)',
                                },
                              }}
                              onClick={() => setShowSQLInterface(prev => ({ ...prev, [db.name]: !prev[db.name] }))}
                            >
                              <Code size={16} color="#3B82F6" />
                              <Typography variant="caption" sx={{ fontWeight: 600, color: '#3B82F6', flex: 1 }}>
                                SQL Query Interface
                              </Typography>
                              <IconButton size="small" sx={{ color: '#3B82F6' }}>
                                {showSQLInterface[db.name] ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                              </IconButton>
                            </Box>
                            <Collapse in={showSQLInterface[db.name]}>
                              <Box sx={{ mb: 2 }}>
                                <SQLQueryInterface databaseName={db.name} />
                              </Box>
                            </Collapse>
                            <Divider sx={{ mb: 2, borderColor: 'rgba(59, 130, 246, 0.2)' }} />
                          </Box>
                        )}

                        {/* LMDB Browser */}
                        {db.type === 'lmdb' && (
                          <Box sx={{ mb: 3 }}>
                            <Box
                              sx={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 1,
                                mb: 1.5,
                                cursor: 'pointer',
                                p: 1.5,
                                borderRadius: '8px',
                                bgcolor: showLMDBBrowser[db.name] ? `${config.color}15` : `${config.color}08`,
                                border: '1px solid',
                                borderColor: showLMDBBrowser[db.name] ? `${config.color}30` : `${config.color}15`,
                                transition: 'all 0.2s',
                                '&:hover': {
                                  bgcolor: `${config.color}15`,
                                  borderColor: `${config.color}40`,
                                },
                              }}
                              onClick={() => setShowLMDBBrowser(prev => ({ ...prev, [db.name]: !prev[db.name] }))}
                            >
                              <SearchIcon size={16} color={config.color} />
                              <Typography variant="caption" sx={{ fontWeight: 600, color: config.color, flex: 1 }}>
                                Browse Data
                              </Typography>
                              <IconButton size="small" sx={{ color: config.color }}>
                                {showLMDBBrowser[db.name] ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                              </IconButton>
                            </Box>
                            <Collapse in={showLMDBBrowser[db.name]}>
                              <Box sx={{ mb: 2 }}>
                                <LMDBBrowser databaseName="session_memory" color={config.color} />
                              </Box>
                            </Collapse>
                            <Divider sx={{ mb: 2, borderColor: `${config.color}20` }} />
                          </Box>
                        )}

                        {/* ChromaDB Browser */}
                        {db.type === 'chromadb' && (
                          <Box sx={{ mb: 3 }}>
                            <Box
                              sx={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 1,
                                mb: 1.5,
                                cursor: 'pointer',
                                p: 1.5,
                                borderRadius: '8px',
                                bgcolor: showChromaDBBrowser[db.name] ? `${config.color}15` : `${config.color}08`,
                                border: '1px solid',
                                borderColor: showChromaDBBrowser[db.name] ? `${config.color}30` : `${config.color}15`,
                                transition: 'all 0.2s',
                                '&:hover': {
                                  bgcolor: `${config.color}15`,
                                  borderColor: `${config.color}40`,
                                },
                              }}
                              onClick={() => {
                                setShowChromaDBBrowser(prev => ({ ...prev, [db.name]: !prev[db.name] }));
                                if (!selectedChromaCollection[db.name]) {
                                  setSelectedChromaCollection(prev => ({ ...prev, [db.name]: 'conversation_segments' }));
                                }
                              }}
                            >
                              <SearchIcon size={16} color={config.color} />
                              <Typography variant="caption" sx={{ fontWeight: 600, color: config.color, flex: 1 }}>
                                Browse Collections
                              </Typography>
                              <IconButton size="small" sx={{ color: config.color }}>
                                {showChromaDBBrowser[db.name] ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                              </IconButton>
                            </Box>
                            <Collapse in={showChromaDBBrowser[db.name]}>
                              <Box sx={{ mb: 2 }}>
                                {/* Collection Selector */}
                                <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                                  {['conversation_segments', 'kg_nodes', 'kg_edges'].map((collection) => (
                                    <Chip
                                      key={collection}
                                      label={collection === 'conversation_segments' ? 'Conversations' : collection === 'kg_nodes' ? 'KG Entities' : 'KG Relations'}
                                      onClick={() => setSelectedChromaCollection(prev => ({ ...prev, [db.name]: collection }))}
                                      sx={{
                                        bgcolor: selectedChromaCollection[db.name] === collection ? `${config.color}30` : `${config.color}10`,
                                        color: selectedChromaCollection[db.name] === collection ? config.color : 'text.secondary',
                                        fontWeight: selectedChromaCollection[db.name] === collection ? 600 : 400,
                                        fontSize: '0.7rem',
                                        cursor: 'pointer',
                                        '&:hover': {
                                          bgcolor: `${config.color}20`,
                                        },
                                      }}
                                    />
                                  ))}
                                </Box>
                                
                                {/* Render appropriate browser based on selection */}
                                {selectedChromaCollection[db.name] === 'conversation_segments' && (
                                  <ChromaDBBrowser collectionName="conversation_segments" color={config.color} />
                                )}
                                {selectedChromaCollection[db.name] === 'kg_nodes' && (
                                  <ChromaDBCollectionBrowser 
                                    collectionName="kg_nodes" 
                                    color={config.color}
                                  />
                                )}
                                {selectedChromaCollection[db.name] === 'kg_edges' && (
                                  <ChromaDBCollectionBrowser 
                                    collectionName="kg_edges" 
                                    color={config.color}
                                  />
                                )}
                              </Box>
                            </Collapse>
                            <Divider sx={{ mb: 2, borderColor: `${config.color}20` }} />
                          </Box>
                        )}

                        {/* Metrics Grid - Above table list */}
                        {metrics.length > 0 && (
                          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 1.5, mb: 2 }}>
                            {metrics.map((metric) => (
                              <Box
                                key={metric.label}
                                sx={{
                                  p: 1.5,
                                  borderRadius: '8px',
                                  bgcolor: `${config.color}08`,
                                  border: '1px solid',
                                  borderColor: `${config.color}20`,
                                }}
                              >
                                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                  {metric.label}
                                </Typography>
                                <Typography variant="body1" sx={{ fontWeight: 600, color: config.color }}>
                                  {metric.value}
                                </Typography>
                              </Box>
                            ))}
                          </Box>
                        )}

                        {/* Storage Utilization for LMDB */}
                        {db.type === 'lmdb' && db.map_size_bytes && db.size_bytes && (
                          <Box sx={{ mb: 2 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                              <Typography variant="caption" color="text.secondary">
                                Storage Utilization
                              </Typography>
                              <Typography variant="caption" sx={{ fontWeight: 600 }}>
                                {((db.size_bytes / db.map_size_bytes) * 100).toFixed(1)}%
                              </Typography>
                            </Box>
                            <LinearProgress
                              variant="determinate"
                              value={(db.size_bytes / db.map_size_bytes) * 100}
                              sx={{
                                height: 8,
                                borderRadius: 4,
                                bgcolor: `${config.color}15`,
                                '& .MuiLinearProgress-bar': {
                                  bgcolor: config.color,
                                  borderRadius: 4,
                                },
                              }}
                            />
                          </Box>
                        )}

                        {/* Table/Collection Browser */}
                        {databaseDetails[db.name] && (
                          <Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                              <List size={16} color={config.color} />
                              <Typography variant="caption" sx={{ fontWeight: 600, color: config.color }}>
                                {db.type === 'libsql' ? 'Tables' : db.type === 'chromadb' ? 'Collections' : 'Databases'}
                              </Typography>
                            </Box>
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                          {/* LibSQL Tables - Compact */}
                          {databaseDetails[db.name].tables?.map((table: TableInfo) => (
                            <Box
                              key={table.name}
                              sx={{
                                p: 1,
                                borderRadius: '6px',
                                bgcolor: `${config.color}06`,
                                border: '1px solid',
                                borderColor: `${config.color}15`,
                                transition: 'all 0.2s',
                                '&:hover': {
                                  bgcolor: `${config.color}10`,
                                  borderColor: `${config.color}30`,
                                  transform: 'translateX(4px)',
                                },
                              }}
                            >
                              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                                  <Table size={12} color={config.color} />
                                  <Typography variant="caption" sx={{ fontWeight: 600, fontFamily: 'monospace', fontSize: '0.75rem' }}>
                                    {table.name}
                                  </Typography>
                                  {table.columns && (
                                    <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.65rem' }}>
                                      ({table.columns} cols)
                                    </Typography>
                                  )}
                                </Box>
                                <Typography variant="caption" sx={{ color: config.color, fontWeight: 600, fontSize: '0.7rem' }}>
                                  {formatNumber(table.row_count)} rows
                                </Typography>
                              </Box>
                            </Box>
                          ))}
                          {/* ChromaDB Collections */}
                          {databaseDetails[db.name].collections?.map((collection: CollectionInfo) => (
                            <Box
                              key={collection.name}
                              sx={{
                                p: 1.5,
                                borderRadius: '8px',
                                bgcolor: `${config.color}08`,
                                border: '1px solid',
                                borderColor: `${config.color}20`,
                                transition: 'all 0.2s',
                                '&:hover': {
                                  bgcolor: `${config.color}12`,
                                  borderColor: `${config.color}40`,
                                  transform: 'translateX(4px)',
                                },
                              }}
                            >
                              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  <Layers size={14} color={config.color} />
                                  <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'monospace' }}>
                                    {collection.name}
                                  </Typography>
                                </Box>
                                <Chip
                                  label={`${formatNumber(collection.document_count)} docs`}
                                  size="small"
                                  sx={{
                                    bgcolor: `${config.color}15`,
                                    color: config.color,
                                    fontSize: '0.65rem',
                                    height: 20,
                                    fontWeight: 600,
                                  }}
                                />
                              </Box>
                              {collection.dimension && (
                                <Typography variant="caption" color="text.secondary">
                                  Dimension: {collection.dimension}
                                </Typography>
                              )}
                            </Box>
                          ))}
                          {/* LMDB Databases */}
                          {databaseDetails[db.name].databases?.map((lmdbDb: LMDBDatabaseInfo) => (
                            <Box
                              key={lmdbDb.name}
                              sx={{
                                p: 1.5,
                                borderRadius: '8px',
                                bgcolor: `${config.color}08`,
                                border: '1px solid',
                                borderColor: `${config.color}20`,
                                transition: 'all 0.2s',
                                '&:hover': {
                                  bgcolor: `${config.color}12`,
                                  borderColor: `${config.color}40`,
                                  transform: 'translateX(4px)',
                                },
                              }}
                            >
                              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  <Key size={14} color={config.color} />
                                  <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'monospace' }}>
                                    {lmdbDb.name}
                                  </Typography>
                                </Box>
                                <Chip
                                  label={`${formatNumber(lmdbDb.key_count)} keys`}
                                  size="small"
                                  sx={{
                                    bgcolor: `${config.color}15`,
                                    color: config.color,
                                    fontSize: '0.65rem',
                                    height: 20,
                                    fontWeight: 600,
                                  }}
                                />
                              </Box>
                            </Box>
                          ))}
                        </Box>
                          </Box>
                        )}
                      </>
                    )}

                        {/* Error Details */}
                        {db.error_details && (
                          <Alert
                            severity={db.status === 'critical' ? 'error' : 'warning'}
                            sx={{
                              mt: 2,
                              fontSize: '0.75rem',
                              '& .MuiAlert-message': { fontSize: '0.75rem' },
                            }}
                          >
                            {db.error_details}
                          </Alert>
                        )}
                  </Box>
                </Collapse>
              </Paper>
            );
          })
        )}
      </Box>
    </Box>
  );
};
