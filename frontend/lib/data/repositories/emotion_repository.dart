import 'package:aico_frontend/networking/clients/unified_api_client.dart';
import 'package:aico_frontend/data/models/emotion_model.dart';

/// Repository for emotion API operations
class EmotionRepository {
  final UnifiedApiClient _apiClient;

  EmotionRepository({
    required UnifiedApiClient apiClient,
  }) : _apiClient = apiClient;

  /// Get current emotional state from backend
  Future<EmotionModel?> getCurrentEmotion() async {
    try {
      print('[EMOTION_REPO] Fetching emotion from /emotion/current');
      final data = await _apiClient.get<Map<String, dynamic>>('/emotion/current');
      
      if (data != null) {
        print('[EMOTION_REPO] Got emotion data: $data');
        return EmotionModel.fromJson(data);
      } else {
        print('[EMOTION_REPO] No emotional state available (null response)');
        return null;
      }
    } catch (e) {
      print('[EMOTION_REPO] Error fetching emotion: $e');
      // Silently fail - emotion is non-critical
      return null;
    }
  }

  /// Get emotional state history with smart filtering
  /// 
  /// Parameters:
  /// - [limit]: Maximum number of records (1-1000, default: 50)
  /// - [hours]: Only return emotions from last N hours
  /// - [days]: Only return emotions from last N days
  /// - [since]: ISO timestamp - only return emotions after this time
  /// - [feeling]: Filter by specific emotion (e.g., 'calm', 'playful')
  /// 
  /// Examples:
  /// - `getEmotionHistory(limit: 100)` - Last 100 emotions
  /// - `getEmotionHistory(days: 7)` - All emotions from last 7 days
  /// - `getEmotionHistory(hours: 24, feeling: 'calm')` - All 'calm' emotions in last 24 hours
  Future<List<EmotionHistoryItem>> getEmotionHistory({
    int limit = 50,
    int? hours,
    int? days,
    String? since,
    String? feeling,
  }) async {
    try {
      // Build query parameters
      final queryParams = <String, String>{
        'limit': limit.toString(),
      };
      
      if (hours != null) queryParams['hours'] = hours.toString();
      if (days != null) queryParams['days'] = days.toString();
      if (since != null) queryParams['since'] = since;
      if (feeling != null) queryParams['feeling'] = feeling;
      
      final queryString = queryParams.entries
          .map((e) => '${e.key}=${Uri.encodeComponent(e.value)}')
          .join('&');
      
      print('[EMOTION_REPO] Fetching emotion history: $queryString');
      final data = await _apiClient.get<Map<String, dynamic>>('/emotion/history?$queryString');
      
      print('[EMOTION_REPO] History response: ${data?['count']} records');
      
      if (data != null && data['history'] != null) {
        final history = (data['history'] as List)
            .map((item) => EmotionHistoryItem.fromJson(item as Map<String, dynamic>))
            .toList();
        print('[EMOTION_REPO] Parsed ${history.length} history items');
        return history;
      } else {
        print('[EMOTION_REPO] No history data in response');
        return [];
      }
    } catch (e) {
      print('[EMOTION_REPO] Error fetching history: $e');
      return [];
    }
  }
}
