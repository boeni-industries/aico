import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, Tabs, Tab, CircularProgress } from '@mui/material';
import {
  Memory as MemoryIcon,
  Storage as StorageIcon,
  AccountTree as GraphIcon,
  AutoAwesome as AmsIcon,
  PhotoAlbum as AlbumIcon,
} from '@mui/icons-material';
import { MemorySystemMap } from '../components/memory/MemorySystemMap';
import { KnowledgeGraphExplorer } from '../components/memory/KnowledgeGraphExplorer';
import { KnowledgeGraphAnalytics } from '../components/memory/KnowledgeGraphAnalytics';
import { WorkingMemoryPanel } from '../components/memory/WorkingMemoryPanel';
import { SemanticMemoryPanel } from '../components/memory/SemanticMemoryPanel';
import { MemoryAlbumPanel } from '../components/memory/MemoryAlbumPanel';
import { AMSPanel } from '../components/memory/AMSPanel';
import { AutoRefreshControls } from '../components/common/AutoRefreshControls';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import { fetchGraphStats, fetchNodes, fetchEdges, KGNode, KGEdge, GraphStats } from '../api/kg';
import { fetchWorkingMemoryStats, fetchSemanticMemoryStats, fetchMemoryAlbum, deleteMemory, deleteMemories, WorkingMemoryStats, SemanticMemoryStats, MemoryAlbumEntry } from '../api/memory';

type MemoryTab = 'working' | 'semantic' | 'knowledge-graph' | 'ams' | 'album';

export const MemoryAmsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<MemoryTab>('working');
  const [graphStats, setGraphStats] = useState<GraphStats | null>(null);
  const [nodes, setNodes] = useState<KGNode[]>([]);
  const [edges, setEdges] = useState<KGEdge[]>([]);
  const [workingStats, setWorkingStats] = useState<WorkingMemoryStats | null>(null);
  const [semanticStats, setSemanticStats] = useState<SemanticMemoryStats | null>(null);
  const [albumEntries, setAlbumEntries] = useState<MemoryAlbumEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadMemoryData = useCallback(async () => {
    try {
      setError(null);

      const [statsData, nodesData, edgesData, workingData, semanticData, albumData] = await Promise.all([
        fetchGraphStats(),
        fetchNodes(1000, 0), // Increased limit to ensure we get all nodes
        fetchEdges(1000, 0), // Increased limit to ensure we get all edges
        fetchWorkingMemoryStats(),
        fetchSemanticMemoryStats(),
        fetchMemoryAlbum(undefined, false, 50, 0),
      ]);

      console.log('KG Data loaded:', {
        totalNodes: statsData.total_nodes,
        fetchedNodes: nodesData.nodes.length,
        totalEdges: statsData.total_edges,
        fetchedEdges: edgesData.edges.length,
        nodeTypes: statsData.node_types,
        edgeTypes: statsData.edge_types
      });

      setGraphStats(statsData);
      setNodes(nodesData.nodes);
      setEdges(edgesData.edges);
      setWorkingStats(workingData);
      setSemanticStats(semanticData);
      setAlbumEntries(albumData.memories);
    } catch (err: any) {
      console.error('Failed to load memory data:', err);
      setError(err.message || 'Failed to load memory data');
    }
  }, []);

  const { isRefreshing, autoRefreshEnabled, toggleAutoRefresh, refresh } = useAutoRefresh({
    onRefresh: loadMemoryData,
    interval: 5000,
    defaultEnabled: true,
  });

  useEffect(() => {
    loadMemoryData();
  }, [loadMemoryData]);

  const memoryTiers = [
    {
      key: 'working',
      label: 'Working',
      icon: <MemoryIcon sx={{ fontSize: 20, color: '#3B82F6' }} />,
      count: workingStats ? `${workingStats.active_items} items` : 'Loading...',
      lastActivity: '2 seconds ago',
      health: 'healthy' as const,
      color: '#3B82F6',
    },
    {
      key: 'semantic',
      label: 'Semantic',
      icon: <StorageIcon sx={{ fontSize: 20, color: '#8B5CF6' }} />,
      count: semanticStats ? `${(semanticStats.total_vectors / 1000).toFixed(1)}K vectors` : 'Loading...',
      lastActivity: '5 minutes ago',
      health: 'healthy' as const,
      color: '#8B5CF6',
    },
    {
      key: 'knowledge-graph',
      label: 'Knowledge Graph',
      icon: <GraphIcon sx={{ fontSize: 20, color: '#10B981' }} />,
      count: `${nodes.length} nodes`,
      lastActivity: '12 minutes ago',
      health: 'healthy' as const,
      color: '#10B981',
    },
    {
      key: 'ams',
      label: 'AMS',
      icon: <AmsIcon sx={{ fontSize: 20, color: '#F59E0B' }} />,
      count: 'Active',
      lastActivity: '1 hour ago',
      health: 'healthy' as const,
      color: '#F59E0B',
    },
    {
      key: 'album',
      label: 'Album',
      icon: <AlbumIcon sx={{ fontSize: 20, color: '#EC4899' }} />,
      count: `${albumEntries.length}`,
      lastActivity: albumEntries.length > 0 ? new Date(albumEntries[0].created_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : 'No memories',
      health: 'healthy' as const,
      color: '#EC4899',
    },
  ];

  // Transform backend data to visualization format
  const transformedNodes = nodes.map((node) => {
    // Count connections for this node
    const connections = edges.filter(
      (edge) => edge.source_id === node.id || edge.target_id === node.id
    ).length;

    return {
      id: node.id,
      label: node.properties.name || node.label,
      type: node.label.toLowerCase() as any,
      connections,
      importance: node.confidence,
      properties: node.properties,
      confidence: node.confidence,
      created_at: node.created_at,
      updated_at: node.updated_at,
      valid_from: node.valid_from,
      valid_until: node.valid_until,
      is_current: node.is_current,
      canonical_id: node.canonical_id,
      aliases: node.aliases,
      source_text: node.source_text,
    };
  });

  const transformedEdges = edges.map((edge) => ({
    source: edge.source_id,
    target: edge.target_id,
    relation_type: edge.relation_type as any,
    strength: edge.confidence,
    properties: edge.properties,
  }));

  // Transform album entries to conversation format for the panel
  const albumConversations = albumEntries.map((entry) => {
    // Format user display: "Full Name (nickname) [user_id]"
    // Handle cases where user data might be missing
    const fullName = entry.user_full_name || 'Unknown User';
    const userUuid = entry.user_uuid || 'unknown';
    
    let userDisplay = fullName;
    if (entry.user_nickname) {
      userDisplay += ` (${entry.user_nickname})`;
    }
    userDisplay += ` [${userUuid.substring(0, 8)}]`;

    return {
      id: entry.fact_id,
      title: entry.content,
      full_content: entry.content,
      timestamp: new Date(entry.created_at).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }),
      person: userDisplay,
      user_uuid: userUuid,
      user_full_name: fullName,
      user_nickname: entry.user_nickname || null,
      sentiment: 'neutral' as const,
      messageCount: 1,
      tags: entry.tags || [],
      contentType: (entry.content_type || 'message') as 'conversation' | 'message',
      conversationTitle: entry.conversation_id ? `Conv ${entry.conversation_id.substring(0, 8)}` : undefined,
      turnRange: entry.message_id ? undefined : 'Multi-turn',
    };
  });

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Page Header with Auto-Refresh Controls */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6, maxWidth: '800px' }}>
          Explore AICO's complete memory architecture: from fast working memory to long-term semantic storage,
          knowledge graph relationships, adaptive consolidation, and your curated conversation album.
        </Typography>
        <AutoRefreshControls
          autoRefreshEnabled={autoRefreshEnabled}
          onToggleAutoRefresh={toggleAutoRefresh}
          onRefresh={refresh}
          isRefreshing={isRefreshing}
        />
      </Box>

      {/* Memory System Map */}
      <MemorySystemMap
        tiers={memoryTiers}
        onTierClick={(key) => setActiveTab(key as MemoryTab)}
        activeTab={activeTab}
      />

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs
          value={activeTab}
          onChange={(_, value) => setActiveTab(value)}
          sx={{
            '& .MuiTab-root': {
              textTransform: 'none',
              fontWeight: 500,
              fontSize: '0.9rem',
            },
          }}
        >
          <Tab label="Working Memory" value="working" />
          <Tab label="Semantic Memory" value="semantic" />
          <Tab label="Knowledge Graph" value="knowledge-graph" />
          <Tab label="AMS" value="ams" />
          <Tab label="Memory Album" value="album" />
        </Tabs>
      </Box>

      {/* Tab Content */}
      <Box sx={{ py: 2 }}>
        {activeTab === 'working' && workingStats && (
          <WorkingMemoryPanel
            activeItems={workingStats.active_items}
            capacity={workingStats.capacity}
            ttlUtilization={workingStats.ttl_utilization_percent}
            evictionRate={workingStats.eviction_rate_per_min}
            recentActivity={workingStats.recent_activity}
          />
        )}

        {activeTab === 'semantic' && semanticStats && (
          <SemanticMemoryPanel
            vectorCount={semanticStats.total_vectors}
            indexSize={`${semanticStats.index_size_mb.toFixed(2)} MB`}
            avgLatency={semanticStats.avg_retrieval_latency_ms}
            collections={semanticStats.collections}
          />
        )}

        {activeTab === 'knowledge-graph' && (
          <>
            {isRefreshing ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
                <CircularProgress />
              </Box>
            ) : error ? (
              <Box sx={{ p: 3, textAlign: 'center' }}>
                <Typography color="error">{error}</Typography>
              </Box>
            ) : (
              <>
                {/* Comprehensive Analytics Dashboard */}
                {graphStats && (
                  <Box sx={{ mb: 3 }}>
                    <KnowledgeGraphAnalytics stats={graphStats} />
                  </Box>
                )}
                
                {/* Graph Explorer */}
                <KnowledgeGraphExplorer
                  nodes={transformedNodes}
                  edges={transformedEdges}
                  stats={graphStats}
                />
              </>
            )}
          </>
        )}

        {activeTab === 'ams' && <AMSPanel />}

        {activeTab === 'album' && (
          <MemoryAlbumPanel 
            conversations={albumConversations} 
            onDelete={async (ids: string[]) => {
              try {
                await deleteMemories(ids);
                // Refresh album data after deletion
                const albumData = await fetchMemoryAlbum();
                setAlbumEntries(albumData.memories);
              } catch (error) {
                console.error('Failed to delete memories:', error);
                throw error;
              }
            }}
          />
        )}
      </Box>
    </Box>
  );
};
