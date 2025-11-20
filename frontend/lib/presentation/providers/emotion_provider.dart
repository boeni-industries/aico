import 'dart:async';

import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/data/models/emotion_model.dart';
import 'package:aico_frontend/data/repositories/emotion_repository.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'emotion_provider.g.dart';

/// Provider for emotion repository
@riverpod
EmotionRepository emotionRepository(Ref ref) {
  final apiClient = ref.watch(unifiedApiClientProvider);
  return EmotionRepository(apiClient: apiClient);
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
    // Poll every 2 seconds when active
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) async {
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
      
      print('[EMOTION_PROVIDER] Fetched emotion: ${emotion?.primary ?? "null"}');
      
      // Check if provider is still mounted before updating state
      if (!ref.mounted) {
        print('[EMOTION_PROVIDER] Provider disposed, skipping state update');
        return;
      }
      
      // Only update if emotion changed
      if (emotion != null && emotion != state) {
        print('[EMOTION_PROVIDER] Updating state to: ${emotion.primary}');
        state = emotion;
      }
    } catch (e) {
      print('[EMOTION_PROVIDER] Error fetching emotion: $e');
      // Silently fail - emotion is non-critical
    }
  }

  /// Manually refresh emotion state
  Future<void> refresh() async {
    await _fetchEmotion();
  }
}
