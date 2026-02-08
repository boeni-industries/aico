import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:aico_frontend/data/models/interaction_model.dart';
import 'package:aico_frontend/data/repositories/interaction_repository.dart';
import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/presentation/providers/auth_provider.dart';

part 'interaction_provider.g.dart';

/// State for interaction management
@immutable
class InteractionState {
  final List<InteractionRequest> interactions;
  final bool isLoading;
  final String? error;
  final bool isWebSocketConnected;

  const InteractionState({
    this.interactions = const [],
    this.isLoading = false,
    this.error,
    this.isWebSocketConnected = false,
  });

  InteractionState copyWith({
    List<InteractionRequest>? interactions,
    bool? isLoading,
    String? error,
    bool? isWebSocketConnected,
  }) {
    return InteractionState(
      interactions: interactions ?? this.interactions,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      isWebSocketConnected: isWebSocketConnected ?? this.isWebSocketConnected,
    );
  }

  /// Get pending interactions
  List<InteractionRequest> get pending => interactions
      .where((i) => i.status == 'pending')
      .toList();

  /// Get deferred interactions
  List<InteractionRequest> get deferred => interactions
      .where((i) => i.status == 'deferred')
      .toList();

  /// Get answered interactions
  List<InteractionRequest> get answered => interactions
      .where((i) => i.status == 'answered')
      .toList();

  /// Get dismissed interactions
  List<InteractionRequest> get dismissed => interactions
      .where((i) => i.status == 'dismissed')
      .toList();

  /// Get required pending interactions
  List<InteractionRequest> get requiredPending => pending
      .where((i) => i.requirement == 'required')
      .toList();

  /// Get high severity pending interactions
  List<InteractionRequest> get highSeverityPending => pending
      .where((i) => i.severity == 'high')
      .toList();
}

/// Interaction repository provider
final interactionRepositoryProvider = Provider<InteractionRepository>((ref) {
  final apiClient = ref.watch(unifiedApiClientProvider);
  return InteractionRepository(
    apiClient: apiClient,
  );
});


/// Main interaction state provider
@riverpod
class Interaction extends _$Interaction {
  StreamSubscription<Map<String, dynamic>>? _wsSubscription;

  @override
  InteractionState build() {
    // Subscribe to WebSocket notifications
    _subscribeToNotifications();

    // Load pending interactions after build completes
    Future.microtask(() => _loadPendingInteractions());

    return const InteractionState();
  }

  /// Subscribe to WebSocket notifications for real-time updates
  void _subscribeToNotifications() {
    try {
      final wsClient = ref.read(webSocketClientProvider);
      final authState = ref.read(authProvider);
      
      final userUuid = authState.user?.id ?? '1e69de47-a3af-4343-8dba-dbf5dcf5f160';
      
      // Subscribe to interaction notifications topic
      final topic = 'interaction.notifications.$userUuid';
      wsClient.subscribe(topic);
      
      // Listen for broadcast messages
      _wsSubscription = wsClient.broadcasts.listen((message) {
        debugPrint('[InteractionProvider] Received WebSocket message: ${message['type']}');
        if (message['type'] == 'broadcast') {
          final data = message['data'] as Map<String, dynamic>?;
          if (data != null) {
            try {
              final broadcastData = InteractionBroadcastData.fromJson(data);
              _handleBroadcast(broadcastData);
            } catch (e) {
              debugPrint('[InteractionProvider] Error parsing broadcast data: $e');
            }
          }
        }
      });
      
      // Cleanup subscription on dispose
      ref.onDispose(() {
        _wsSubscription?.cancel();
      });
      
      debugPrint('[InteractionProvider] Subscribed to $topic');
    } catch (e) {
      debugPrint('[InteractionProvider] Failed to subscribe to WebSocket: $e');
    }
  }

  /// Load pending interactions from backend
  Future<void> _loadPendingInteractions() async {
    state = state.copyWith(isLoading: true);

    try {
      final repository = ref.read(interactionRepositoryProvider);
      debugPrint('[InteractionProvider] Fetching pending interactions...');
      
      final response = await repository.listInteractions(
        status: 'pending',
        limit: 100,
      );
      
      debugPrint('[InteractionProvider] Response: $response');
      debugPrint('[InteractionProvider] Items count: ${response['total']}');

      final interactions = (response['items'] as List)
          .map((json) => InteractionRequest.fromJson(json as Map<String, dynamic>))
          .toList();

      debugPrint('[InteractionProvider] Loaded ${interactions.length} interactions');
      
      state = state.copyWith(
        interactions: interactions,
        isLoading: false,
        error: null,
      );
    } catch (e) {
      debugPrint('[InteractionProvider] Error loading pending: $e');
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Refresh all interactions
  Future<void> refresh() async {
    await _loadPendingInteractions();
  }

  /// Load interaction history
  Future<void> loadHistory({int limit = 50}) async {
    try {
      final repository = ref.read(interactionRepositoryProvider);
      final response = await repository.listInteractions(
        limit: limit,
      );

      final interactions = (response['interactions'] as List)
          .map((json) => InteractionRequest.fromJson(json as Map<String, dynamic>))
          .toList();

      state = state.copyWith(
        interactions: interactions,
        error: null,
      );
    } catch (e) {
      debugPrint('[InteractionProvider] Error loading history: $e');
      state = state.copyWith(error: e.toString());
    }
  }

  /// Handle WebSocket broadcast
  void _handleBroadcast(InteractionBroadcastData broadcast) {
    debugPrint('[InteractionProvider] Received broadcast: ${broadcast.interaction.interactionId}');

    // Update or add interaction
    final updated = _upsertInteraction(broadcast.interaction);
    state = state.copyWith(interactions: updated);

    // Show notification for new interactions
    if (broadcast.event.eventType == 'created' &&
        broadcast.interaction.requirement == 'required') {
      _showNotification(broadcast.interaction);
    }
  }

  /// Upsert interaction in list
  List<InteractionRequest> _upsertInteraction(InteractionRequest interaction) {
    final index = state.interactions.indexWhere(
      (i) => i.interactionId == interaction.interactionId,
    );

    if (index >= 0) {
      // Update existing
      final updated = List<InteractionRequest>.from(state.interactions);
      updated[index] = interaction;
      return updated;
    } else {
      // Add new
      return [...state.interactions, interaction];
    }
  }

  /// Show local notification
  void _showNotification(InteractionRequest interaction) {
    // TODO: Implement local notifications
    debugPrint('[InteractionProvider] Notification: ${interaction.prompt}');
  }

  /// Answer a question/choice/dialogue interaction
  Future<void> answer(String interactionId, {String? text, Map<String, dynamic>? json}) async {
    try {
      final repository = ref.read(interactionRepositoryProvider);
      final response = await repository.answerInteraction(
        interactionId,
        answerText: text,
        answerJson: json,
      );

      final interaction = InteractionRequest.fromJson(
        response['interaction'] as Map<String, dynamic>,
      );

      final updated = _upsertInteraction(interaction);
      state = state.copyWith(interactions: updated, error: null);
    } catch (e) {
      debugPrint('[InteractionProvider] Error answering: $e');
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  /// Approve an approval interaction
  Future<void> approve(String interactionId) async {
    try {
      final repository = ref.read(interactionRepositoryProvider);
      final response = await repository.approveInteraction(interactionId);

      final interaction = InteractionRequest.fromJson(
        response['interaction'] as Map<String, dynamic>,
      );

      final updated = _upsertInteraction(interaction);
      state = state.copyWith(interactions: updated, error: null);
    } catch (e) {
      debugPrint('[InteractionProvider] Error approving: $e');
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  /// Reject an approval interaction
  Future<void> reject(String interactionId) async {
    try {
      final repository = ref.read(interactionRepositoryProvider);
      final response = await repository.rejectInteraction(interactionId);

      final interaction = InteractionRequest.fromJson(
        response['interaction'] as Map<String, dynamic>,
      );

      final updated = _upsertInteraction(interaction);
      state = state.copyWith(interactions: updated, error: null);
    } catch (e) {
      debugPrint('[InteractionProvider] Error rejecting: $e');
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  /// Cancel an interaction
  Future<void> cancel(String interactionId) async {
    try {
      final repository = ref.read(interactionRepositoryProvider);
      final response = await repository.cancelInteraction(interactionId);

      final interaction = InteractionRequest.fromJson(
        response['interaction'] as Map<String, dynamic>,
      );

      final updated = _upsertInteraction(interaction);
      state = state.copyWith(interactions: updated, error: null);
    } catch (e) {
      debugPrint('[InteractionProvider] Error cancelling: $e');
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  /// Defer an interaction (mark as "later")
  Future<void> defer(String interactionId) async {
    // Optimistic update
    final interaction = state.interactions.firstWhere(
      (i) => i.interactionId == interactionId,
    );

    // Create new instance with updated status (no copyWith in @JsonSerializable)
    final deferred = InteractionRequest(
      interactionId: interaction.interactionId,
      userId: interaction.userId,
      correlationId: interaction.correlationId,
      interactionType: interaction.interactionType,
      status: 'deferred',
      prompt: interaction.prompt,
      title: interaction.title,
      requirement: interaction.requirement,
      severity: interaction.severity,
      category: interaction.category,
      expectedAnswerType: interaction.expectedAnswerType,
      allowedOptions: interaction.allowedOptions,
      answerText: interaction.answerText,
      answerJson: interaction.answerJson,
      answeredAt: interaction.answeredAt,
      expiresAt: interaction.expiresAt,
      idempotencyKey: interaction.idempotencyKey,
      createdAt: interaction.createdAt,
      updatedAt: interaction.updatedAt,
    );
    final updated = _upsertInteraction(deferred);
    state = state.copyWith(interactions: updated);

    // TODO: Schedule reminder based on severity
    _scheduleReminder(interaction);
  }

  /// Schedule reminder for deferred interaction
  void _scheduleReminder(InteractionRequest interaction) {
    // TODO: Implement reminder scheduling
    debugPrint('[InteractionProvider] Reminder scheduled for ${interaction.interactionId}');
  }
}
