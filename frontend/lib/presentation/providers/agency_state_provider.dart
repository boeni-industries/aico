import 'dart:async';

import 'package:aico_frontend/data/models/agency_model.dart';
import 'package:aico_frontend/domain/providers/agency_providers.dart';
import 'package:flutter/foundation.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'agency_state_provider.g.dart';

/// Agency badge state for displaying current agency focus
/// Manages visual feedback through the badge indicator on avatar
class AgencyBadgeState {
  final AgencyBadgeMode mode;
  final double intensity; // 0.0 to 1.0 - affects pulse speed and glow
  final String? intentionSummary; // Brief text for current intention
  final int pendingCount; // Number of pending items (lessons, etc.)
  final Map<String, dynamic> metadata; // Additional context
  
  const AgencyBadgeState({
    this.mode = AgencyBadgeMode.none,
    this.intensity = 0.5,
    this.intentionSummary,
    this.pendingCount = 0,
    this.metadata = const {},
  });
  
  AgencyBadgeState copyWith({
    AgencyBadgeMode? mode,
    double? intensity,
    String? intentionSummary,
    int? pendingCount,
    Map<String, dynamic>? metadata,
  }) {
    return AgencyBadgeState(
      mode: mode ?? this.mode,
      intensity: intensity ?? this.intensity,
      intentionSummary: intentionSummary ?? this.intentionSummary,
      pendingCount: pendingCount ?? this.pendingCount,
      metadata: metadata ?? this.metadata,
    );
  }
  
  bool get isVisible => mode != AgencyBadgeMode.none;
}

/// Agency badge display modes - each with distinct visual characteristics
enum AgencyBadgeMode {
  /// No badge visible - no active agency state
  none,
  
  /// Active intention - purple dot, subtle pulse
  activeIntention,
  
  /// Lesson pending review - amber dot, attention pulse
  lessonPending,
  
  /// Goal in progress - progress ring, rotating shimmer
  goalProgress,
  
  /// Goal completed - green burst, brief celebration
  goalCompleted,
  
  /// Multiple items - badge with count indicator
  multipleItems,
}

/// Provider for agency badge state
@riverpod
class AgencyBadgeStateNotifier extends _$AgencyBadgeStateNotifier {
  Timer? _pollTimer;
  
  @override
  AgencyBadgeState build() {
    // Start polling for agency state when provider is initialized
    _startPolling();
    
    // Clean up timer on dispose
    ref.onDispose(() {
      _pollTimer?.cancel();
    });
    
    return const AgencyBadgeState();
  }
  
  /// Start periodic polling of agency state
  void _startPolling() {
    // Poll immediately
    _fetchAndUpdateState();
    
    // Then poll every 30 seconds
    _pollTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      _fetchAndUpdateState();
    });
  }
  
  /// Fetch agency state from backend and update UI state
  Future<void> _fetchAndUpdateState() async {
    try {
      final repository = ref.read(agencyRepositoryProvider);
      final agencyState = await repository.getAgencyState();
      
      // Map backend state to UI badge state
      _mapAgencyStateToUI(agencyState);
    } catch (e) {
      if (kDebugMode) {
        print('Failed to fetch agency state: $e');
      }
      // On error, hide badge
      hide();
    }
  }
  
  /// Map backend AgencyStateModel to UI badge state
  void _mapAgencyStateToUI(AgencyStateModel agencyState) {
    // Priority order:
    // 1. Consent required actions (lessons pending) - highest priority
    // 2. Primary focus (active intention)
    // 3. Curiosity opportunities (goal progress)
    // 4. Multiple active intentions
    // 5. No badge
    
    if (agencyState.consentRequiredActions.isNotEmpty) {
      // Lessons or actions need user approval
      showLessonPending(
        count: agencyState.consentRequiredActions.length,
        intensity: 0.8,
      );
    } else if (agencyState.intentionSet.primaryFocus != null) {
      // Active intention/focus
      final focus = agencyState.intentionSet.primaryFocus!;
      showActiveIntention(
        summary: focus.title,
        intensity: focus.score ?? 0.6,
      );
    } else if (agencyState.curiosityStatus.curiosityOpportunities.isNotEmpty) {
      // Curiosity opportunities available
      final opportunity = agencyState.curiosityStatus.curiosityOpportunities.first;
      showGoalProgress(
        progress: opportunity.intensity,
        goalName: opportunity.theme,
      );
    } else if (agencyState.intentionSet.activeIntentions.length > 1) {
      // Multiple active intentions
      showMultipleItems(
        count: agencyState.intentionSet.activeIntentions.length,
        summary: '${agencyState.intentionSet.activeIntentions.length} active intentions',
      );
    } else {
      // No active agency state
      hide();
    }
  }
  
  /// Manually refresh agency state (for pull-to-refresh, etc.)
  Future<void> refresh() async {
    await _fetchAndUpdateState();
  }
  
  /// Set badge to active intention mode
  void showActiveIntention({
    required String summary,
    double intensity = 0.6,
  }) {
    state = state.copyWith(
      mode: AgencyBadgeMode.activeIntention,
      intentionSummary: summary,
      intensity: intensity,
    );
  }
  
  /// Set badge to lesson pending mode
  void showLessonPending({
    int count = 1,
    double intensity = 0.8,
  }) {
    state = state.copyWith(
      mode: AgencyBadgeMode.lessonPending,
      pendingCount: count,
      intensity: intensity,
    );
  }
  
  /// Set badge to goal progress mode
  void showGoalProgress({
    required double progress, // 0.0 to 1.0
    String? goalName,
  }) {
    state = state.copyWith(
      mode: AgencyBadgeMode.goalProgress,
      intensity: progress,
      metadata: goalName != null ? {'goal': goalName, 'progress': progress} : {},
    );
  }
  
  /// Show goal completed celebration
  void showGoalCompleted({
    String? goalName,
    Duration duration = const Duration(seconds: 3),
  }) {
    state = state.copyWith(
      mode: AgencyBadgeMode.goalCompleted,
      intensity: 1.0,
      metadata: goalName != null ? {'goal': goalName} : {},
    );
    
    // Auto-hide after duration
    Future.delayed(duration, () {
      if (state.mode == AgencyBadgeMode.goalCompleted) {
        hide();
      }
    });
  }
  
  /// Show multiple items indicator
  void showMultipleItems({
    required int count,
    String? summary,
  }) {
    state = state.copyWith(
      mode: AgencyBadgeMode.multipleItems,
      pendingCount: count,
      intentionSummary: summary,
      intensity: 0.7,
    );
  }
  
  /// Hide badge
  void hide() {
    state = const AgencyBadgeState(mode: AgencyBadgeMode.none);
  }
  
  /// Update intensity without changing mode
  void updateIntensity(double intensity) {
    state = state.copyWith(intensity: intensity.clamp(0.0, 1.0));
  }
  
  /// Update pending count
  void updatePendingCount(int count) {
    state = state.copyWith(pendingCount: count);
  }
}
