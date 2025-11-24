import 'dart:async';

import 'package:aico_frontend/domain/entities/tts_state.dart';

/// Abstract TTS repository contract for clean architecture.
abstract class TtsRepository {
  /// Current TTS state snapshot.
  TtsState get currentState;

  /// Stream of state updates for UI observers.
  Stream<TtsState> get stateStream;

  /// Initialize the TTS engine and load any required models.
  Future<void> initialize();

  /// Speak the provided text using the active TTS engine.
  Future<void> speak(String text);

  /// Stop any ongoing speech.
  Future<void> stop();

  /// Pause current speech if supported.
  Future<void> pause();

  /// Resume paused speech if supported.
  Future<void> resume();

  /// Download the neural TTS model, reporting progress from 0.0–1.0.
  Future<void> downloadModel({
    required Function(double progress) onProgress,
  });

  /// Whether the neural TTS model is already downloaded and available.
  Future<bool> isModelDownloaded();

  /// Clean up any underlying resources.
  Future<void> dispose();
}
