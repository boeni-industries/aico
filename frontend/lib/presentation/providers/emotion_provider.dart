import 'dart:async';

import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/data/models/emotion_model.dart';
import 'package:aico_frontend/data/repositories/emotion_repository.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'emotion_provider.g.dart';

/// Repository provider
@riverpod
EmotionRepository emotionRepository(Ref ref) {
  return EmotionRepository(apiClient: ref.watch(unifiedApiClientProvider));
}

/// Emotion history provider - fetches and caches emotion history
/// 
/// Supports smart filtering:
/// - [limit]: Max records (default: 50)
/// - [hours]: Last N hours
/// - [days]: Last N days
/// - [since]: ISO timestamp
/// - [feeling]: Filter by emotion
@riverpod
Future<List<EmotionHistoryItem>> emotionHistory(
  Ref ref, {
  int limit = 50,
  int? hours,
  int? days,
  String? since,
  String? feeling,
}) async {
  final repository = ref.watch(emotionRepositoryProvider);
  return repository.getEmotionHistory(
    limit: limit,
    hours: hours,
    days: days,
    since: since,
    feeling: feeling,
  );
}

/// Provider for current emotion state with polling
@riverpod
class EmotionState extends _$EmotionState {
  Timer? _pollTimer;
  
  @override
  EmotionModel? build() {
    // Start polling when provider is initialized
    _startPolling();
    
    // Cancel polling when provider is disposed
    ref.onDispose(() {
      _stopPolling();
    });
    
    return null;
  }

  void _startPolling() {
    // Poll every 5 seconds when active (reduced from 2s to minimize console spam)
    _pollTimer = Timer.periodic(const Duration(seconds: 5), (_) async {
      await _fetchEmotion();
    });
    
    // Fetch immediately on start
    _fetchEmotion();
  }

  void _stopPolling() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  Future<void> _fetchEmotion() async {
    try {
      final repository = ref.read(emotionRepositoryProvider);
      final emotion = await repository.getCurrentEmotion();
      
      // Check if provider is still mounted before updating state
      if (!ref.mounted) {
        return;
      }
      
      // Only update if emotion changed
      if (emotion != null && emotion != state) {
        state = emotion;
        
        // Invalidate emotion history cache to trigger refresh
        ref.invalidate(emotionHistoryProvider);
      }
    } catch (e) {
      // Silently fail - emotion is non-critical
    }
  }

  /// Manually refresh emotion state
  Future<void> refresh() async {
    await _fetchEmotion();
  }
}
