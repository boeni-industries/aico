import 'package:equatable/equatable.dart';

/// Engine type for TTS synthesis.
enum TtsEngine {
  /// Neural Kokoro on-device TTS
  neural,
}

/// High-level status of the TTS system.
enum TtsStatus {
  idle,
  initializing,
  speaking,
  error,
}

/// Immutable TTS state entity used by the domain and presentation layers.
class TtsState extends Equatable {
  final TtsStatus status;
  final TtsEngine? engine;
  final String? currentText;
  final double progress;
  final bool isModelDownloaded;
  final String? errorMessage;

  const TtsState({
    required this.status,
    this.engine,
    this.currentText,
    this.progress = 0.0,
    this.isModelDownloaded = false,
    this.errorMessage,
  });

  factory TtsState.initial() => const TtsState(
        status: TtsStatus.idle,
        engine: null,
        currentText: null,
        progress: 0.0,
        isModelDownloaded: false,
        errorMessage: null,
      );

  TtsState copyWith({
    TtsStatus? status,
    TtsEngine? engine,
    String? currentText,
    double? progress,
    bool? isModelDownloaded,
    String? errorMessage,
  }) {
    return TtsState(
      status: status ?? this.status,
      engine: engine ?? this.engine,
      currentText: currentText ?? this.currentText,
      progress: progress ?? this.progress,
      isModelDownloaded: isModelDownloaded ?? this.isModelDownloaded,
      errorMessage: errorMessage ?? this.errorMessage,
    );
  }

  bool get isSpeaking => status == TtsStatus.speaking;
  bool get hasError => status == TtsStatus.error && errorMessage != null;

  @override
  List<Object?> get props => [
        status,
        engine,
        currentText,
        progress,
        isModelDownloaded,
        errorMessage,
      ];
}
