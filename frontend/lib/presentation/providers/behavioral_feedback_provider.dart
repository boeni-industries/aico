/// Behavioral Feedback Provider
/// 
/// State management for behavioral learning feedback using Riverpod 3.x.
/// Handles submitting user feedback on AI responses.
library;

import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/data/datasources/remote/behavioral_remote_datasource.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'behavioral_feedback_provider.g.dart';

/// State for feedback submission
class FeedbackState {
  final bool isSubmitting;
  final String? error;
  final String? successMessageId; // Track which message was successfully rated

  const FeedbackState({
    this.isSubmitting = false,
    this.error,
    this.successMessageId,
  });

  FeedbackState copyWith({
    bool? isSubmitting,
    String? error,
    String? successMessageId,
  }) {
    return FeedbackState(
      isSubmitting: isSubmitting ?? this.isSubmitting,
      error: error,
      successMessageId: successMessageId ?? this.successMessageId,
    );
  }
}

/// Provider for behavioral remote datasource
@riverpod
BehavioralRemoteDataSource behavioralRemoteDataSource(Ref ref) {
  final apiClient = ref.watch(unifiedApiClientProvider);
  return BehavioralRemoteDataSource(apiClient);
}

/// Provider for feedback state management
@riverpod
class BehavioralFeedback extends _$BehavioralFeedback {
  @override
  FeedbackState build() {
    return const FeedbackState();
  }

  /// Submit feedback for a message
  /// 
  /// Args:
  ///   messageId: ID of the message being rated
  ///   isPositive: true for thumbs up, false for thumbs down
  ///   reason: Optional quick tag category
  ///   freeText: Optional detailed feedback text
  Future<bool> submitFeedback({
    required String messageId,
    required bool isPositive,
    String? reason,
    String? freeText,
  }) async {
    print('📊 [FEEDBACK_PROVIDER] Starting feedback submission');
    print('📊 [FEEDBACK_PROVIDER] messageId: $messageId, isPositive: $isPositive');
    
    // Keep provider alive during async operation
    final link = ref.keepAlive();
    print('📊 [FEEDBACK_PROVIDER] Provider kept alive');
    
    // Check if provider is still mounted
    if (!ref.mounted) {
      print('📊 [FEEDBACK_PROVIDER] ❌ Provider not mounted, aborting');
      link.close();
      return false;
    }
    
    // Set submitting state
    state = state.copyWith(isSubmitting: true, error: null);
    print('📊 [FEEDBACK_PROVIDER] State set to submitting');

    try {
      final dataSource = ref.read(behavioralRemoteDataSourceProvider);
      print('📊 [FEEDBACK_PROVIDER] Got data source');
      
      // Convert boolean to reward value
      final reward = isPositive ? 1 : -1;
      print('📊 [FEEDBACK_PROVIDER] Reward value: $reward');
      
      // Submit feedback
      print('📊 [FEEDBACK_PROVIDER] Calling API...');
      final response = await dataSource.submitFeedback(
        messageId: messageId,
        reward: reward,
        reason: reason,
        freeText: freeText,
      );
      print('📊 [FEEDBACK_PROVIDER] ✅ API call successful');
      print('📊 [FEEDBACK_PROVIDER] Response: $response');
      
      // Check if still mounted after async operation
      if (!ref.mounted) {
        print('📊 [FEEDBACK_PROVIDER] ❌ Provider unmounted after API call');
        return false;
      }
      
      // Log success
      print('📊 [FEEDBACK_PROVIDER] Logging success...');
      AICOLog.info(
        'Behavioral feedback submitted',
        topic: 'BehavioralFeedbackProvider',
        extra: {
          'message_id': messageId,
          'reward': reward,
          'has_reason': reason != null,
          'has_free_text': freeText != null,
          'event_id': response['event_id'],
          'skill_updated': response['skill_updated'],
          'new_confidence': response['new_confidence'] ?? 'null',
        },
      );
      
      // Update state with success
      print('📊 [FEEDBACK_PROVIDER] Updating state to success');
      state = state.copyWith(
        isSubmitting: false,
        successMessageId: messageId,
      );
      
      print('📊 [FEEDBACK_PROVIDER] ✅ Feedback submission complete');
      link.close();
      return true;
    } catch (e) {
      print('📊 [FEEDBACK_PROVIDER] ❌ Error caught: $e');
      print('📊 [FEEDBACK_PROVIDER] Error type: ${e.runtimeType}');
      
      // Check if still mounted after error
      if (!ref.mounted) {
        print('📊 [FEEDBACK_PROVIDER] Provider unmounted after error');
        return false;
      }
      
      // Log error
      AICOLog.error(
        'Failed to submit behavioral feedback',
        topic: 'BehavioralFeedbackProvider',
        error: e,
        extra: {'message_id': messageId},
      );
      
      // Update state with error
      state = state.copyWith(
        isSubmitting: false,
        error: e.toString(),
      );
      
      link.close();
      return false;
    }
  }

  /// Clear error state
  void clearError() {
    state = state.copyWith(error: null);
  }

  /// Clear success state
  void clearSuccess() {
    state = state.copyWith(successMessageId: null);
  }
}
