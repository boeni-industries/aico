import 'package:riverpod_annotation/riverpod_annotation.dart';

import 'package:aico_frontend/data/repositories/tts_repository_impl.dart';
import 'package:aico_frontend/domain/entities/tts_state.dart';
import 'package:aico_frontend/domain/repositories/tts_repository.dart';

part 'tts_provider.g.dart';

/// TTS repository provider
@riverpod
TtsRepository ttsRepository(Ref ref) {
  final repository = TtsRepositoryImpl();
  ref.onDispose(() => repository.dispose());
  return repository;
}

/// TTS state notifier using modern Riverpod pattern
@riverpod
class Tts extends _$Tts {
  late final TtsRepository _repository;

  @override
  TtsState build() {
    // Keep a reference to the repository to prevent disposal issues
    _repository = ref.watch(ttsRepositoryProvider);
    _initialize();
    _listenToStateChanges();
    return TtsState.initial();
  }

  Future<void> _initialize() async {
    await _repository.initialize();
  }

  void _listenToStateChanges() {
    _repository.stateStream.listen((newState) {
      state = newState;
    });
  }

  /// Speak text using TTS (fire-and-forget, non-blocking)
  void speak(String text) {
    // Don't await - let it run in background
    _repository.speak(text);
  }

  /// Stop current speech
  Future<void> stop() async {
    await _repository.stop();
  }

  /// Pause current speech
  Future<void> pause() async {
    await _repository.pause();
  }

  /// Resume paused speech
  Future<void> resume() async {
    await _repository.resume();
  }

  /// Download neural TTS model
  Future<void> downloadModel({
    required Function(double progress) onProgress,
  }) async {
    await _repository.downloadModel(onProgress: onProgress);
  }

  /// Check if model is downloaded
  Future<bool> isModelDownloaded() async {
    return await _repository.isModelDownloaded();
  }
}
