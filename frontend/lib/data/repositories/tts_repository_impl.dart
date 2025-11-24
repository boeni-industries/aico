import 'dart:async';
import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/domain/entities/tts_state.dart';
import 'package:aico_frontend/domain/repositories/tts_repository.dart';
import 'package:kokoro_tts_flutter/kokoro_tts_flutter.dart'; 

/// TTS repository implementation with neural TTS (bundled model)
class TtsRepositoryImpl implements TtsRepository {
  final _stateController = StreamController<TtsState>.broadcast();
  TtsState _currentState = TtsState.initial();

  Kokoro? _kokoro;
  Tokenizer? _tokenizer;
  bool _isAvailable = false;

  TtsRepositoryImpl();

  @override
  Future<void> initialize() async {
    try {
      _updateState(_currentState.copyWith(status: TtsStatus.initializing));

      // Model is bundled in assets - just load it
      const config = KokoroConfig(
        modelPath: 'assets/tts/kokoro-v1.0.onnx',
        voicesPath: 'assets/tts/voices.json',
      );

      _kokoro = Kokoro(config);
      await _kokoro!.initialize();

      _tokenizer = Tokenizer();
      await _tokenizer!.ensureInitialized();

      _isAvailable = true;

      _updateState(_currentState.copyWith(
        status: TtsStatus.idle,
        engine: TtsEngine.neural,
        isModelDownloaded: true,
      ));

      AICOLog.info('Neural TTS initialized successfully');
    } catch (e, stackTrace) {
      _isAvailable = false;
      AICOLog.error(
        'TTS initialization failed - this is a deployment bug',
        error: e,
        stackTrace: stackTrace,
      );
      _updateState(_currentState.copyWith(
        status: TtsStatus.error,
        errorMessage: 'TTS initialization failed: ${e.toString()}',
      ));
    }
  }


  @override
  Future<void> speak(String text) async {
    if (text.isEmpty) {
      AICOLog.warn('Attempted to speak empty text');
      return;
    }

    if (!_isAvailable) {
      AICOLog.warn('TTS unavailable - silent mode');
      return;
    }

    try {
      _updateState(_currentState.copyWith(
        status: TtsStatus.speaking,
        currentText: text,
        progress: 0.0,
      ));

      // Phonemize text first
      final phonemes = await _tokenizer!.phonemize(text, lang: 'en-us');

      // Generate speech
      final ttsResult = await _kokoro!.createTTS(
        text: phonemes,
        voice: 'af_heart',
        isPhonemes: true,
      );

      AICOLog.info('TTS synthesis completed: ${ttsResult.audio.length} samples');

      _updateState(_currentState.copyWith(
        status: TtsStatus.idle,
        currentText: null,
        progress: 1.0,
      ));
    } catch (e, stackTrace) {
      AICOLog.error('TTS synthesis failed', error: e, stackTrace: stackTrace);
      _isAvailable = false; // Disable for session
      _updateState(_currentState.copyWith(
        status: TtsStatus.error,
        errorMessage: 'Voice synthesis failed: ${e.toString()}',
      ));
    }
  }


  @override
  Future<void> stop() async {
    if (!_isAvailable || _kokoro == null) return;

    try {
      // Kokoro doesn't have a stop method - synthesis is synchronous
      // Just update state
      _updateState(_currentState.copyWith(
        status: TtsStatus.idle,
        currentText: null,
        progress: 0.0,
      ));
    } catch (e, stackTrace) {
      AICOLog.error('TTS stop failed', error: e, stackTrace: stackTrace);
    }
  }

  @override
  Future<void> pause() async {
    // Kokoro doesn't support pause - would need custom implementation
    AICOLog.warn('TTS pause not supported');
  }

  @override
  Future<void> resume() async {
    // Kokoro doesn't support resume - would need custom implementation
    AICOLog.warn('TTS resume not supported');
  }

  @override
  Future<bool> isModelDownloaded() async {
    // Model is bundled in assets - always available
    return true;
  }

  @override
  Future<void> downloadModel({
    required Function(double progress) onProgress,
  }) async {
    // Model is bundled in assets - no download needed
    AICOLog.info('Model bundled in assets - no download required');
    onProgress(1.0);
  }

  @override
  Stream<TtsState> get stateStream => _stateController.stream;

  @override
  TtsState get currentState => _currentState;

  void _updateState(TtsState newState) {
    _currentState = newState;
    _stateController.add(newState);
  }

  @override
  Future<void> dispose() async {
    await _stateController.close();
    if (_isAvailable && _kokoro != null) {
      _kokoro!.dispose();
    }
  }
}
