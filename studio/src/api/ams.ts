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
