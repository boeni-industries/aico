import 'package:aico_frontend/data/models/proactive_model.dart';
import 'package:aico_frontend/domain/providers/proactive_providers.dart';
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
  @override
  ProactiveState build() {
    // Schedule async fetch after build completes
    Future.microtask(() => fetchPendingInitiations());
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
}
