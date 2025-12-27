/**
 * Agency API Types
 * 
 * TypeScript interfaces matching backend API models for agency system.
 */

export type GoalOrigin = 'user' | 'curiosity' | 'hobby' | 'maintenance';
export type GoalStatus = 'pending' | 'active' | 'paused' | 'completed' | 'retired';
export type GoalPriority = 'low' | 'normal' | 'high' | 'critical';
export type CuriosityLevel = 'low' | 'medium' | 'high';
export type ProactiveBehaviorLevel = 'quiet' | 'balanced' | 'proactive';
export type PolicyEffect = 'allow' | 'allow_with_warning' | 'needs_consent' | 'block';

export interface GoalSummary {
  goal_id: string;
  title: string;
  description?: string;
  origin: GoalOrigin;
  priority: GoalPriority;
  status: GoalStatus;
  score?: number;
  priority_band?: string;
  created_at: string;
  metadata: Record<string, any>;
}

export interface IntentionSetResponse {
  user_id: string;
  primary_focus?: GoalSummary;
  active_intentions: GoalSummary[];
  open_goals_total: number;
  hobby_goals_active: GoalSummary[];
  timestamp: string;
}

export interface CuriosityOpportunity {
  theme: string;
  description: string;
  intensity: number;
  signal_type: string;
}

export interface CuriosityStatusResponse {
  user_id: string;
  curiosity_level: CuriosityLevel;
  curiosity_opportunities: CuriosityOpportunity[];
  curiosity_goals_active: number;
  timestamp: string;
}

export interface ValueProfileResponse {
  profile_id: string;
  user_id: string;
  curiosity_intensity: number;
  proactive_behavior_level: ProactiveBehaviorLevel;
  sensitive_life_areas: string[];
  allowed_curiosity_domains: string[];
}

export interface PolicyRuleResponse {
  rule_id: string;
  rule_name: string;
  target_type: string;
  effect: PolicyEffect;
  scope: string;
  priority: number;
  conditions: Record<string, any>;
  user_message?: string;
  enabled: boolean;
}

export interface PolicyListResponse {
  policies: PolicyRuleResponse[];
  total: number;
}

export interface ConsentResponse {
  consent_id: string;
  user_id: string;
  scope: Record<string, any>;
  decision: string;
  granted_at: string;
}

export interface ConsentListResponse {
  consents: ConsentResponse[];
  total: number;
}

export interface AgencyStateResponse {
  user_id: string;
  intention_set: IntentionSetResponse;
  curiosity_status: CuriosityStatusResponse;
  value_profile: ValueProfileResponse;
  consent_required_actions: any[];
  timestamp: string;
}

export interface GoalResponse {
  goal_id: string;
  user_id: string;
  origin: GoalOrigin;
  goal_type: string;
  title: string;
  description: string;
  status: GoalStatus;
  priority: GoalPriority;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface GoalListResponse {
  goals: GoalResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface AgencyMetrics {
  active_goals: number;
  plans_in_flight: number;
  proactive_messages_24h: number;
  curiosity_level: CuriosityLevel;
  reflection_runs_7d: number;
  lessons_applied: number;
}
