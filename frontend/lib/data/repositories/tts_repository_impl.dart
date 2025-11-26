import 'dart:async';

import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/domain/entities/tts_state.dart';
import 'package:aico_frontend/domain/repositories/tts_repository.dart';
import 'package:just_audio/just_audio.dart';

/// TTS repository implementation with backend streaming
class TtsRepositoryImpl implements TtsRepository {
  final _stateController = StreamController<TtsState>.broadcast();
  TtsState _currentState = TtsState.initial();
  bool _isDisposed = false;

  AudioPlayer? _audioPlayer;
  bool _isAvailable = false;

  TtsRepositoryImpl();

  @override
  Future<void> initialize() async {
    if (_isAvailable) {
      AICOLog.info('TTS already initialized, skipping');
      return;
    }

    try {
      AICOLog.info('🎤 Initializing TTS (backend streaming)...');
      _updateState(_currentState.copyWith(status: TtsStatus.initializing));

      _audioPlayer = AudioPlayer();
      _isAvailable = true;

      _updateState(_currentState.copyWith(
        status: TtsStatus.idle,
        engine: TtsEngine.neural,
        isModelDownloaded: true,
      ));

      AICOLog.info('✅ TTS initialized - ready for backend streaming');
    } catch (e, stackTrace) {
      _isAvailable = false;
      AICOLog.error('TTS initialization failed', error: e, stackTrace: stackTrace);
      _updateState(_currentState.copyWith(
        status: TtsStatus.error,
        errorMessage: 'TTS initialization failed: ${e.toString()}',
      ));
    }
  }

  @override
  Future<void> speak(String text) async {
    if (text.isEmpty || !_isAvailable) return;

    try {
      _updateState(_currentState.copyWith(
        status: TtsStatus.speaking,
        currentText: text,
        progress: 0.0,
      ));
      
      // TODO: Request TTS from backend and stream audio
      AICOLog.info('🎤 TTS backend integration pending');
      
      await Future.delayed(const Duration(milliseconds: 100));
      _updateState(_currentState.copyWith(
        status: TtsStatus.idle,
        currentText: null,
        progress: 1.0,
      ));
    } catch (e, stackTrace) {
      AICOLog.error('TTS speak failed', error: e, stackTrace: stackTrace);
      _updateState(_currentState.copyWith(
        status: TtsStatus.error,
        errorMessage: 'TTS failed: ${e.toString()}',
      ));
    }
  }

  @override
  Future<void> stop() async {
    if (!_isAvailable || _currentState.status != TtsStatus.speaking) return;
    await _audioPlayer?.stop();
    _updateState(_currentState.copyWith(
      status: TtsStatus.idle,
      currentText: null,
      progress: 0.0,
    ));
  }

  @override
  Future<void> pause() async {}

  @override
  Future<void> resume() async {}

  @override
  Future<bool> isModelDownloaded() async => true;

  @override
  Future<void> downloadModel({required Function(double progress) onProgress}) async {
    onProgress(1.0);
  }

  @override
  Stream<TtsState> get stateStream => _stateController.stream;

  @override
  TtsState get currentState => _currentState;

  void _updateState(TtsState newState) {
    if (_isDisposed) return;
    _currentState = newState;
    if (!_stateController.isClosed) {
      _stateController.add(newState);
    }
  }

  @override
  Future<void> dispose() async {
    if (_isDisposed) return;
    _isDisposed = true;
    await _audioPlayer?.dispose();
    if (!_stateController.isClosed) {
      await _stateController.close();
    }
  }
}
