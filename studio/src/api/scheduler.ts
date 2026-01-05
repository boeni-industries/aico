/**
 * Scheduler & Jobs API Client
 * 
 * Provides API functions for interacting with AICO's task scheduler system.
 */

import { httpJson } from './http';

const BASE_URL = '/scheduler';

// ============================================================================
// Types
// ============================================================================

export interface Task {
  task_id: string;
  task_class: string;
  schedule: string;
  config: Record<string, any> | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface TaskExecution {
  execution_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'skipped' | 'deferred';
  started_at: string;
  completed_at: string | null;
  result: Record<string, any> | null;
  error_message: string | null;
  duration_seconds: number | null;
}

export interface TaskWithStatus extends Task {
  last_execution: TaskExecution | null;
  next_run_time: string | null;
  is_running: boolean;
}

export interface SchedulerStatus {
  running: boolean;
  registered_tasks: number;
  scheduled_tasks: number;
  running_tasks: number;
  next_run_times: Record<string, string>;
}

export interface TaskListResponse {
  tasks: Task[];
  total_count: number;
}

export interface TaskExecutionHistoryResponse {
  task_id: string;
  executions: TaskExecution[];
  total_count: number;
}

export interface TaskTriggerResponse {
  success: boolean;
  message: string;
  execution_id: string | null;
  data: Record<string, any> | null;
}

export interface CreateTaskRequest {
  task_id: string;
  task_class: string;
  schedule: string;
  config?: Record<string, any>;
  enabled?: boolean;
}

export interface UpdateTaskRequest {
  schedule?: string;
  config?: Record<string, any>;
  enabled?: boolean;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Get scheduler status and statistics
 */
export async function fetchSchedulerStatus(): Promise<SchedulerStatus> {
  return httpJson<SchedulerStatus>({
    method: 'GET',
    path: `${BASE_URL}/status`,
  });
}

/**
 * List all scheduled tasks
 */
export async function fetchTasks(enabledOnly: boolean = false): Promise<TaskListResponse> {
  const params = new URLSearchParams();
  if (enabledOnly) {
    params.append('enabled_only', 'true');
  }
  
  return httpJson<TaskListResponse>({
    method: 'GET',
    path: `${BASE_URL}/tasks${params.toString() ? `?${params.toString()}` : ''}`,
  });
}

/**
 * Get task details including status
 */
export async function fetchTaskDetails(taskId: string): Promise<TaskWithStatus> {
  return httpJson<TaskWithStatus>({
    method: 'GET',
    path: `${BASE_URL}/tasks/${taskId}`,
  });
}

/**
 * Get task execution history
 */
export async function fetchTaskExecutions(
  taskId: string,
  limit: number = 50,
  offset: number = 0
): Promise<TaskExecutionHistoryResponse> {
  const params = new URLSearchParams({
    limit: limit.toString(),
  });
  
  return httpJson<TaskExecutionHistoryResponse>({
    method: 'GET',
    path: `${BASE_URL}/tasks/${taskId}/history?${params.toString()}`,
  });
}

/**
 * Get specific execution details
 */
export async function fetchExecutionDetails(executionId: string): Promise<TaskExecution> {
  return httpJson<TaskExecution>({
    method: 'GET',
    path: `${BASE_URL}/executions/${executionId}`,
  });
}

/**
 * Manually trigger a task
 */
export async function triggerTask(taskId: string): Promise<TaskTriggerResponse> {
  return httpJson<TaskTriggerResponse>({
    method: 'POST',
    path: `${BASE_URL}/tasks/${taskId}/trigger`,
  });
}

/**
 * Create a new scheduled task
 */
export async function createTask(request: CreateTaskRequest): Promise<Task> {
  return httpJson<Task>({
    method: 'POST',
    path: `${BASE_URL}/tasks`,
    body: request,
  });
}

/**
 * Update an existing task
 */
export async function updateTask(taskId: string, request: UpdateTaskRequest): Promise<Task> {
  return httpJson<Task>({
    method: 'PUT',
    path: `${BASE_URL}/tasks/${taskId}`,
    body: request,
  });
}

/**
 * Delete a task
 */
export async function deleteTask(taskId: string): Promise<{ success: boolean; message: string }> {
  return httpJson<{ success: boolean; message: string }>({
    method: 'DELETE',
    path: `${BASE_URL}/tasks/${taskId}`,
  });
}

/**
 * Enable a task
 */
export async function enableTask(taskId: string): Promise<Task> {
  return updateTask(taskId, { enabled: true });
}

/**
 * Disable a task
 */
export async function disableTask(taskId: string): Promise<Task> {
  return updateTask(taskId, { enabled: false });
}

/**
 * Get queue statistics
 */
export async function fetchQueueStats(): Promise<Record<string, number>> {
  const status = await fetchSchedulerStatus();
  // Extract queue sizes from status if available
  // This may need adjustment based on actual API response
  return {
    user_facing: 0,
    background_light: 0,
    background_heavy: 0,
    maintenance: 0,
  };
}

/**
 * Get expected number of job runs today based on cron schedules
 */
export async function fetchExpectedRunsToday(): Promise<{
  total_expected_runs: number;
  task_run_counts: Record<string, number>;
  calculated_at: string;
  period_start: string;
  period_end: string;
}> {
  return httpJson({
    method: 'GET',
    path: `${BASE_URL}/expected-runs-today`,
  });
}
