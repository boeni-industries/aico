import { httpJson } from './http';

// ============================================================================
// AMS Types
// ============================================================================

export interface ConsolidationStatus {
  last_run: string | null;
  next_scheduled: string;
  current_cycle_day: number;
  total_cycle_days: number;
  status: 'idle' | 'running' | 'scheduled';
  last_session: {
    experiences_replayed: number;
    facts_consolidated: number;
    graph_updates: {
      entities: number;
      relationships: number;
    };
    duration_seconds: number;
    success: boolean;
    completed_at: string;
  } | null;
}

export interface SkillInfo {
  skill_id: string;
  name: string;
  confidence: number;
  usage_count: number;
  last_feedback: 'positive' | 'negative' | 'neutral' | null;
  last_used: string | null;
}

export interface BehavioralLearningStats {
  active_skills: number;
  total_feedback_received: number;
  learning_rate: string;
  average_confidence: number;
  top_skills: SkillInfo[];
  recent_learning_insights: string[];
}

export interface PreferenceDimension {
  name: string;
  value: number;
  label: string;
}

export interface UserPreferences {
  dimensions: PreferenceDimension[];
  context_buckets: number;
  insights: string[];
}

export interface FeedbackStats {
  total: number;
  positive: number;
  negative: number;
  neutral: number;
  response_rate: number;
  recent_feedback: Array<{
    time: string;
    message: string;
    skill: string;
    type: 'positive' | 'negative' | 'neutral';
  }>;
}

export interface AMSStats {
  consolidation: ConsolidationStatus;
  behavioral_learning: BehavioralLearningStats;
  user_preferences: UserPreferences;
  feedback: FeedbackStats;
}

export interface SkillDetail {
  skill_id: string;
  skill_name: string;
  skill_type: string;
  status: string;
  confidence_score: number | null;
  usage_count: number | null;
  positive_count: number | null;
  negative_count: number | null;
  last_used_at: string | null;
  created_at: string;
}

export interface SkillOverview {
  total_skills: number;
  active_skills: number;
  skills: SkillDetail[];
}

export interface MemoryMetricsSnapshot {
  timestamp: string;
  working_memory_count: number;
  semantic_facts_count: number;
  knowledge_graph_entities: number;
  knowledge_graph_relationships: number;
  total_conversations: number;
}

export interface MemoryGrowthStats {
  period_days: number;
  facts_added: number;
  entities_added: number;
  relationships_added: number;
  consolidation_sessions: number;
}

export interface MemoryEvolution {
  current_metrics: MemoryMetricsSnapshot;
  growth_7d: MemoryGrowthStats;
  growth_30d: MemoryGrowthStats;
  historical_snapshots: MemoryMetricsSnapshot[];
  insights: string[];
}

// ============================================================================
// API Functions
// ============================================================================

export async function fetchAMSStats(): Promise<AMSStats> {
  const response = await httpJson<AMSStats>({
    method: 'GET',
    path: '/ams/stats',
  });
  return response;
}

export async function fetchConsolidationStatus(): Promise<ConsolidationStatus> {
  const response = await httpJson<ConsolidationStatus>({
    method: 'GET',
    path: '/ams/consolidation/status',
  });
  return response;
}

export async function fetchBehavioralLearningStats(): Promise<BehavioralLearningStats> {
  const response = await httpJson<BehavioralLearningStats>({
    method: 'GET',
    path: '/ams/behavioral/stats',
  });
  return response;
}

export async function fetchUserPreferences(): Promise<UserPreferences> {
  const response = await httpJson<UserPreferences>({
    method: 'GET',
    path: '/ams/preferences',
  });
  return response;
}

export async function fetchFeedbackStats(): Promise<FeedbackStats> {
  const response = await httpJson<FeedbackStats>({
    method: 'GET',
    path: '/ams/feedback/stats',
  });
  return response;
}

export async function fetchSkillOverview(): Promise<SkillOverview> {
  const response = await httpJson<SkillOverview>({
    method: 'GET',
    path: '/ams/skills/overview',
  });
  return response;
}

export async function fetchMemoryEvolution(): Promise<MemoryEvolution> {
  const response = await httpJson<MemoryEvolution>({
    method: 'GET',
    path: '/ams/memory/evolution',
  });
  return response;
}
