import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, Tabs, Tab } from '@mui/material';
import { AutoRefreshControls } from '../components/common/AutoRefreshControls';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import { OperationsOverview } from '../components/operations/OperationsOverview';

type OperationsTab = 'overview' | 'topology' | 'users' | 'scheduler' | 'logs' | 'bus' | 'gateway' | 'database' | 'metrics';

export const OperationsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<OperationsTab>('overview');

  const loadOperationsData = useCallback(async () => {
    // TODO: Replace with actual API calls per tab
    console.log('Loading operations data for tab:', activeTab);
  }, [activeTab]);

  const { isRefreshing, autoRefreshEnabled, toggleAutoRefresh, refresh } = useAutoRefresh({
    onRefresh: loadOperationsData,
    interval: 5000,
    defaultEnabled: true,
  });

  const handleTabChange = (_event: React.SyntheticEvent, newValue: OperationsTab) => {
    setActiveTab(newValue);
  };

  const handleNavigateToTab = (tab: string) => {
    setActiveTab(tab as OperationsTab);
  };

  useEffect(() => {
    loadOperationsData();
  }, [loadOperationsData]);

  return (
    <Box sx={{ p: 3 }}>
      {/* Page Header */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', mb: 3 }}>
        <AutoRefreshControls
          autoRefreshEnabled={autoRefreshEnabled}
          onToggleAutoRefresh={toggleAutoRefresh}
          onRefresh={refresh}
          isRefreshing={isRefreshing}
        />
      </Box>

      {/* Tab Navigation */}
      <Box sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            '& .MuiTab-root': {
              textTransform: 'none',
              fontWeight: 600,
              fontSize: '0.9rem',
              minHeight: 48,
            },
          }}
        >
          <Tab label="Overview" value="overview" />
          <Tab label="System Topology" value="topology" />
          <Tab label="Users & Sessions" value="users" />
          <Tab label="Scheduler & Jobs" value="scheduler" />
          <Tab label="Logs & Events" value="logs" />
          <Tab label="Message Bus" value="bus" />
          <Tab label="API Gateway" value="gateway" />
          <Tab label="Database & Storage" value="database" />
          <Tab label="System Metrics" value="metrics" />
        </Tabs>
      </Box>

      {/* Tab Content */}
      <Box>
        {activeTab === 'overview' && <OperationsOverview onNavigateToTab={handleNavigateToTab} />}
        {activeTab === 'topology' && <Typography>System Topology - Coming Soon</Typography>}
        {activeTab === 'users' && <Typography>Users & Sessions - Coming Soon</Typography>}
        {activeTab === 'scheduler' && <Typography>Scheduler & Jobs - Coming Soon</Typography>}
        {activeTab === 'logs' && <Typography>Logs & Events - Coming Soon</Typography>}
        {activeTab === 'bus' && <Typography>Message Bus - Coming Soon</Typography>}
        {activeTab === 'gateway' && <Typography>API Gateway - Coming Soon</Typography>}
        {activeTab === 'database' && <Typography>Database & Storage - Coming Soon</Typography>}
        {activeTab === 'metrics' && <Typography>System Metrics - Coming Soon</Typography>}
      </Box>
    </Box>
  );
};
