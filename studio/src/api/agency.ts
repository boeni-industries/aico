/**
 * Agency API Client
 * 
 * Functions for fetching agency data from backend API.
 */

import { httpJson } from './http';
import {
  AgencyStateResponse,
  IntentionSetResponse,
  CuriosityStatusResponse,
  ValueProfileResponse,
  PolicyListResponse,
  ConsentListResponse,
  GoalResponse,
  GoalListResponse,
  GoalOrigin,
  GoalStatus,
  GoalPriority,
} from '../types/agency';

export interface IntentionSetParams {
  limit?: number;
}

export async function fetchIntentionSet(
  params?: IntentionSetParams
): Promise<IntentionSetResponse> {
  return httpJson<IntentionSetResponse>({
    method: 'GET',
    path: '/agency/intentions',
    query: {
      limit: params?.limit,
    },
  });
}

export async function fetchCuriosityStatus(): Promise<CuriosityStatusResponse> {
  return httpJson<CuriosityStatusResponse>({
    method: 'GET',
    path: '/agency/curiosity',
  });
}

export async function fetchValueProfile(): Promise<ValueProfileResponse> {
  return httpJson<ValueProfileResponse>({
    method: 'GET',
    path: '/agency/profile',
  });
}

export async function fetchPolicies(targetType?: string): Promise<PolicyListResponse> {
  return httpJson<PolicyListResponse>({
    method: 'GET',
    path: '/agency/policies',
    query: {
      target_type: targetType,
    },
  });
}

export async function fetchConsents(): Promise<ConsentListResponse> {
  return httpJson<ConsentListResponse>({
    method: 'GET',
    path: '/agency/consent',
  });
}

export async function fetchAgencyState(): Promise<AgencyStateResponse> {
  return httpJson<AgencyStateResponse>({
    method: 'GET',
    path: '/agency/state',
  });
}

export interface GoalListParams {
  status?: GoalStatus;
  origin?: GoalOrigin;
  priority?: GoalPriority;
  limit?: number;
  page?: number;
}

export async function fetchGoals(params?: GoalListParams): Promise<GoalListResponse> {
  return httpJson<GoalListResponse>({
    method: 'GET',
    path: '/agency/goals',
    query: {
      status: params?.status,
      origin: params?.origin,
      priority: params?.priority,
      limit: params?.limit,
      page: params?.page,
    },
  });
}

export async function fetchGoal(goalId: string): Promise<GoalResponse> {
  return httpJson<GoalResponse>({
    method: 'GET',
    path: `/agency/goals/${goalId}`,
  });
}
