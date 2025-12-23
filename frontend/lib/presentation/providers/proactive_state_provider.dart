import 'dart:async';

import 'package:aico_frontend/data/models/proactive_model.dart';
import 'package:aico_frontend/domain/providers/proactive_providers.dart';
import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/presentation/providers/auth_provider.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'proactive_state_provider.g.dart';

/// State for proactive conversations
class ProactiveState {
  final List<InitiationModel> pendingInitiations;
  final List<InitiationModel> historyInitiations;
  final bool isLoading;
  final String? error;

  const ProactiveState({
    this.pendingInitiations = const [],
    this.historyInitiations = const [],
    this.isLoading = false,
    this.error,
  });

  ProactiveState copyWith({
    List<InitiationModel>? pendingInitiations,
    List<InitiationModel>? historyInitiations,
    bool? isLoading,
    String? error,
  }) {
    return ProactiveState(
      pendingInitiations: pendingInitiations ?? this.pendingInitiations,
      historyInitiations: historyInitiations ?? this.historyInitiations,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Provider for proactive conversation state
@riverpod
class ProactiveStateNotifier extends _$ProactiveStateNotifier {
  StreamSubscription? _wsSubscription;
  
  @override
  ProactiveState build() {
    // Schedule async fetch after build completes
    Future.microtask(() => fetchPendingInitiations());
    
    // Subscribe to WebSocket notifications
    Future.microtask(() => _subscribeToNotifications());
    
    // Clean up subscription on dispose
    ref.onDispose(() {
      _wsSubscription?.cancel();
    });
    
    return const ProactiveState();
  }

  /// Fetch pending initiations from backend
  Future<void> fetchPendingInitiations() async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final repository = ref.read(proactiveRepositoryProvider);
      final initiations = await repository.getPendingInitiations();
      
      state = state.copyWith(
        pendingInitiations: initiations,
        isLoading: false,
      );
    } catch (e) {
      print('🔔 [PROACTIVE] ❌ Error fetching initiations: $e');
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Respond to a proactive initiation
  Future<void> respondToInitiation({
    required String initiationId,
    required String responseType,
    String? responseText,
    double? engagementScore,
  }) async {
    try {
      final repository = ref.read(proactiveRepositoryProvider);
      final request = InitiationResponseRequest(
        initiationId: initiationId,
        responseType: responseType,
        responseText: responseText,
        engagementScore: engagementScore,
      );
      
      await repository.respondToInitiation(request);
      
      // Remove from pending list
      state = state.copyWith(
        pendingInitiations: state.pendingInitiations
            .where((i) => i.initiationId != initiationId)
            .toList(),
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  /// Dismiss an initiation
  Future<void> dismissInitiation(String initiationId) async {
    await respondToInitiation(
      initiationId: initiationId,
      responseType: 'dismissed',
    );
  }

  /// Defer an initiation
  Future<void> deferInitiation(String initiationId) async {
    await respondToInitiation(
      initiationId: initiationId,
      responseType: 'deferred',
    );
  }

  /// Answer an initiation
  Future<void> answerInitiation({
    required String initiationId,
    required String responseText,
    double? engagementScore,
  }) async {
    await respondToInitiation(
      initiationId: initiationId,
      responseType: 'answered',
      responseText: responseText,
      engagementScore: engagementScore,
    );
  }

  /// Fetch history of all initiations
  Future<void> fetchHistory() async {
    try {
      final repository = ref.read(proactiveRepositoryProvider);
      final history = await repository.getInitiationHistory();
      
      state = state.copyWith(
        historyInitiations: history,
      );
    } catch (e) {
      print('🔔 [PROACTIVE] ❌ Error fetching history: $e');
      state = state.copyWith(error: e.toString());
    }
  }
  
  /// Subscribe to WebSocket notifications for real-time updates
  void _subscribeToNotifications() {
    try {
      final wsClient = ref.read(webSocketClientProvider);
      final authState = ref.read(authProvider);
      
      if (authState.user?.id == null) {
        print('🔔 [PROACTIVE] ⚠️ No user UUID, skipping WebSocket subscription');
        return;
      }
      
      final userUuid = authState.user!.id;
      
      // Subscribe to user-specific proactive notification topic
      wsClient.subscribe('proactive.notifications.$userUuid');
      
      // Listen for broadcast messages
      _wsSubscription = wsClient.broadcasts.listen((message) {
        print('🔔 [PROACTIVE] 📨 Received WebSocket message: ${message['type']}');
        if (message['type'] == 'broadcast') {
          final data = message['data'] as Map<String, dynamic>?;
          print('🔔 [PROACTIVE] 📦 Broadcast data type: ${data?['type']}');
          if (data != null && data['type'] == 'new_initiation') {
            _handleNewNotification(data);
          }
        }
      });
      
      print('🔔 [PROACTIVE] 📡 Subscribed to WebSocket notifications for user ${userUuid.substring(0, 8)}');
    } catch (e) {
      print('🔔 [PROACTIVE] ⚠️ Failed to subscribe to WebSocket notifications: $e');
    }
  }
  
  /// Handle new notification received via WebSocket
  void _handleNewNotification(Map<String, dynamic> data) {
    try {
      // Create InitiationModel from WebSocket data
      final newInitiation = InitiationModel(
        initiationId: data['initiation_id'] as String,
        question: data['question'] as String,
        initiatedAt: data['initiated_at'] as String,
        resolutionStatus: data['resolution_status'] as String? ?? 'pending',
        userId: '', // Not provided in broadcast
        conversationId: '', // Not provided in broadcast
      );
      
      // Add to pending list if not already present
      final exists = state.pendingInitiations.any(
        (i) => i.initiationId == newInitiation.initiationId
      );
      
      if (!exists) {
        state = state.copyWith(
          pendingInitiations: [...state.pendingInitiations, newInitiation],
        );
        
        print('🔔 [PROACTIVE] ✅ New notification received via WebSocket: ${newInitiation.initiationId.substring(0, 8)}');
        print('🔔 [PROACTIVE] 📊 Total pending initiations: ${state.pendingInitiations.length}');
      } else {
        print('🔔 [PROACTIVE] ⚠️ Duplicate notification ignored: ${newInitiation.initiationId.substring(0, 8)}');
      }
    } catch (e) {
      print('🔔 [PROACTIVE] ❌ Error handling WebSocket notification: $e');
    }
  }
}
