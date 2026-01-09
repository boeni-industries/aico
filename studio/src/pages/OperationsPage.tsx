import React, { useState, useCallback } from 'react';
import { Box, Typography, Tabs, Tab } from '@mui/material';
import { AutoRefreshControls } from '../components/common/AutoRefreshControls';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import { OperationsOverview } from '../components/operations/OperationsOverview';
import { SystemTopology } from '../components/operations/SystemTopology';
import { UsersSessions } from '../components/operations/UsersSessions';
import { SchedulerJobs } from '../components/operations/SchedulerJobs';
import { LogsEvents } from '../components/operations/LogsEvents';
import { DatabaseStorage } from '../components/operations/DatabaseStorage';
import { MetricsPage } from './MetricsPage';

type OperationsTab = 'overview' | 'topology' | 'users' | 'scheduler' | 'logs' | 'database' | 'metrics';

export const OperationsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<OperationsTab>('overview');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const loadOperationsData = useCallback(async () => {
    // Trigger refresh in child components by incrementing counter
    setRefreshTrigger(prev => prev + 1);
  }, []);

  const { isRefreshing, autoRefreshEnabled, toggleAutoRefresh, refresh } = useAutoRefresh({
    onRefresh: loadOperationsData,
    interval: 5000, // 5 seconds - components handle updates intelligently
    defaultEnabled: true, // Enabled - components prevent jarring updates
  });

  const handleTabChange = (_event: React.SyntheticEvent, newValue: OperationsTab) => {
    setActiveTab(newValue);
  };

  const handleNavigateToTab = (tab: string) => {
    setActiveTab(tab as OperationsTab);
  };

  return (
    <Box sx={{ 
      p: 3, 
      width: '100%',
      maxWidth: '1400px', 
      mx: 'auto',
      minHeight: '100vh'
    }}>
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
          <Tab label="Database & Storage" value="database" />
          <Tab label="System Metrics" value="metrics" />
        </Tabs>
      </Box>

      {/* Tab Content */}
      <Box>
        {activeTab === 'overview' && <OperationsOverview onNavigateToTab={handleNavigateToTab} refreshTrigger={refreshTrigger} />}
        {activeTab === 'topology' && <SystemTopology refreshTrigger={refreshTrigger} />}
        {activeTab === 'users' && <UsersSessions refreshTrigger={refreshTrigger} />}
        {activeTab === 'scheduler' && <SchedulerJobs refreshTrigger={refreshTrigger} />}
        {activeTab === 'logs' && <LogsEvents />}
        {activeTab === 'database' && <DatabaseStorage refreshTrigger={refreshTrigger} />}
        {activeTab === 'metrics' && <MetricsPage />}
      </Box>
    </Box>
  );
};
