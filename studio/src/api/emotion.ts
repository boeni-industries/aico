import { httpJson } from './http';

export interface EmotionHistoryItemDto {
  timestamp: string;
  feeling: string;
  valence: number;
  arousal: number;
  intensity: number;
}

export interface EmotionHistoryResponseDto {
  count: number;
  history: EmotionHistoryItemDto[];
}

export interface EmotionHistoryQuery {
  limit?: number;
  hours?: number;
  days?: number;
  since?: string;
  feeling?: string;
}

export async function fetchEmotionHistory(
  query: EmotionHistoryQuery = {},
): Promise<EmotionHistoryResponseDto> {
  return httpJson<EmotionHistoryResponseDto>({
    method: 'GET',
    path: '/emotion/history',
    query: {
      limit: query.limit ?? 200,
      hours: query.hours,
      days: query.days,
      since: query.since,
      feeling: query.feeling,
    },
  });
}
