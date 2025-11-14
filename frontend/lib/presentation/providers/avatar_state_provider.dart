import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'avatar_state_provider.g.dart';

/// Avatar ring state for immersive information display
/// Manages visual feedback through the avatar's pulsating rings
class AvatarRingState {
  final AvatarMode mode;
  final double intensity; // 0.0 to 1.0 - affects pulse speed and expansion
  final Map<String, dynamic> metadata; // Additional context for specific modes
  
  const AvatarRingState({
    this.mode = AvatarMode.idle,
    this.intensity = 0.5,
    this.metadata = const {},
  });
  
  AvatarRingState copyWith({
    AvatarMode? mode,
    double? intensity,
    Map<String, dynamic>? metadata,
  }) {
    return AvatarRingState(
      mode: mode ?? this.mode,
      intensity: intensity ?? this.intensity,
      metadata: metadata ?? this.metadata,
    );
  }
}

/// Avatar display modes - each with distinct visual characteristics
enum AvatarMode {
  /// Default state - gentle breathing
  idle,
  
  /// AICO is processing/thinking - purple rings, faster pulse
  thinking,
  
  /// AICO is listening (voice input) - blue rings, steady pulse
  listening,
  
  /// AICO is speaking (voice output) - animated based on audio
  speaking,
  
  /// System is connecting - blue rings, fast pulse
  connecting,
  
  /// Error state - red rings, slow pulse or static
  error,
  
  /// Warning/attention needed - amber rings, medium pulse
  attention,
  
  /// Success/celebration - bright green, energetic pulse
  success,
  
  /// Processing intensive task - purple, very fast pulse
  processing,
}

/// Provider for avatar ring state
@riverpod
class AvatarRingStateNotifier extends _$AvatarRingStateNotifier {
  @override
  AvatarRingState build() {
    return const AvatarRingState();
  }
  
  /// Set avatar to thinking mode
  void startThinking({double intensity = 0.8}) {
    state = state.copyWith(
      mode: AvatarMode.thinking,
      intensity: intensity,
    );
  }
  
  /// Set avatar to listening mode (voice input)
  void startListening({double intensity = 0.6}) {
    state = state.copyWith(
      mode: AvatarMode.listening,
      intensity: intensity,
    );
  }
  
  /// Set avatar to speaking mode (voice output)
  void startSpeaking({double intensity = 0.7, Map<String, dynamic>? audioData}) {
    state = state.copyWith(
      mode: AvatarMode.speaking,
      intensity: intensity,
      metadata: audioData ?? {},
    );
  }
  
  /// Set avatar to processing mode (intensive task)
  void startProcessing({double intensity = 1.0, String? taskName}) {
    state = state.copyWith(
      mode: AvatarMode.processing,
      intensity: intensity,
      metadata: taskName != null ? {'task': taskName} : {},
    );
  }
  
  /// Show success state briefly
  void showSuccess({Duration duration = const Duration(seconds: 2)}) {
    state = state.copyWith(
      mode: AvatarMode.success,
      intensity: 0.9,
    );
    
    // Auto-return to idle after duration
    Future.delayed(duration, () {
      if (state.mode == AvatarMode.success) {
        returnToIdle();
      }
    });
  }
  
  /// Show error state
  void showError({String? errorMessage}) {
    state = state.copyWith(
      mode: AvatarMode.error,
      intensity: 0.3,
      metadata: errorMessage != null ? {'error': errorMessage} : {},
    );
  }
  
  /// Show attention/warning state
  void showAttention({String? message}) {
    state = state.copyWith(
      mode: AvatarMode.attention,
      intensity: 0.6,
      metadata: message != null ? {'message': message} : {},
    );
  }
  
  /// Return to idle state
  void returnToIdle() {
    state = const AvatarRingState(
      mode: AvatarMode.idle,
      intensity: 0.5,
    );
  }
  
  /// Update intensity without changing mode
  void updateIntensity(double intensity) {
    state = state.copyWith(intensity: intensity.clamp(0.0, 1.0));
  }
}
