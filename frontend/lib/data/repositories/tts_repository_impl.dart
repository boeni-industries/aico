import 'dart:async';
import 'dart:typed_data';
import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/core/services/tts_isolate_service.dart';
import 'package:aico_frontend/domain/entities/tts_state.dart';
import 'package:aico_frontend/domain/repositories/tts_repository.dart';
import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';
import 'package:uuid/uuid.dart'; 

/// TTS repository implementation with neural TTS (bundled model)
class TtsRepositoryImpl implements TtsRepository {
  final _stateController = StreamController<TtsState>.broadcast();
  TtsState _currentState = TtsState.initial();
  bool _isDisposed = false;

  TtsIsolateService? _isolateService;
  AudioPlayer? _audioPlayer;
  bool _isAvailable = false;
  final _uuid = const Uuid();

  TtsRepositoryImpl();

  @override
  Future<void> initialize() async {
    // Prevent re-initialization if already available
    if (_isAvailable) {
      AICOLog.info('TTS already initialized, skipping');
      return;
    }

    try {
      AICOLog.info('🎤 Starting TTS initialization...');
      _updateState(_currentState.copyWith(status: TtsStatus.initializing));

      // Initialize TTS isolate service for zero-blocking synthesis
      _isolateService = TtsIsolateService(
        modelPath: 'assets/tts/kokoro-v1.0.onnx',
        voicesPath: 'assets/tts/voices.json',
      );
      await _isolateService!.initialize();

      _audioPlayer = AudioPlayer();

      // Set available BEFORE state update to ensure it's set even if state update is blocked
      _isAvailable = true;
      AICOLog.info('🎤 TTS availability flag set to true');

      _updateState(_currentState.copyWith(
        status: TtsStatus.idle,
        engine: TtsEngine.neural,
        isModelDownloaded: true,
      ));

      AICOLog.info('✅ Neural TTS initialized successfully - ready to speak');
    } catch (e, stackTrace) {
      _isAvailable = false;
      AICOLog.error(
        'TTS initialization failed',
        error: e,
        stackTrace: stackTrace,
      );
      
      // Print detailed error for debugging
      debugPrint('🔴 TTS INIT ERROR: ${e.toString()}');
      debugPrint('🔴 TTS INIT ERROR TYPE: ${e.runtimeType}');
      debugPrint('🔴 TTS INIT STACK TRACE:\n$stackTrace');
      
      _updateState(_currentState.copyWith(
        status: TtsStatus.error,
        errorMessage: 'TTS initialization failed: ${e.toString()}',
      ));
    }
  }


  @override
  Future<void> speak(String text) async {
    AICOLog.info('🎤 TTS speak() called with ${text.length} chars');
    debugPrint('🎤 [TTS] speak() - _isAvailable: $_isAvailable, _isDisposed: $_isDisposed, _isolateService: ${_isolateService != null}, _audioPlayer: ${_audioPlayer != null}');
    
    if (text.isEmpty) {
      AICOLog.warn('Attempted to speak empty text');
      return;
    }

    if (!_isAvailable) {
      AICOLog.warn('TTS unavailable - _isAvailable=$_isAvailable, _isolateService=${_isolateService != null}, _audioPlayer=${_audioPlayer != null}');
      debugPrint('🔴 [TTS] BLOCKED: _isAvailable is false!');
      return;
    }

    try {
      AICOLog.info('🎤 Setting TTS status to speaking');
      _updateState(_currentState.copyWith(
        status: TtsStatus.speaking,
        currentText: text,
        progress: 0.0,
      ));

      // Split text into chunks to avoid 510 phoneme limit
      final chunks = _splitTextIntoChunks(text, maxChars: 350); // Increased for fewer chunks
      AICOLog.info('🎤 Split text into ${chunks.length} chunks');

      // Pre-synthesize first chunk in background isolate (ZERO UI BLOCKING!)
      TtsSynthesisResult currentResult = await _isolateService!.synthesize(
        TtsSynthesisRequest(
          id: _uuid.v4(),
          text: chunks[0],
          voice: 'af_heart',
          speed: 1.0,
        ),
      );
      AICOLog.info('🎤 First chunk synthesized in ${currentResult.synthesisTime.inMilliseconds}ms');

      for (int i = 0; i < chunks.length; i++) {
        AICOLog.info('🎤 Playing chunk ${i + 1}/${chunks.length}');

        // Start synthesizing next chunk in background while playing current
        Future<TtsSynthesisResult>? nextChunkFuture;
        if (i + 1 < chunks.length) {
          nextChunkFuture = _isolateService!.synthesize(
            TtsSynthesisRequest(
              id: _uuid.v4(),
              text: chunks[i + 1],
              voice: 'af_heart',
              speed: 1.0,
            ),
          );
        }

        // Convert current chunk to WAV
        final audioBytes = _convertToWav(currentResult.audioSamples, currentResult.sampleRate);

        // Play the audio
        await _audioPlayer!.setAudioSource(
          _RawAudioSource(audioBytes, sampleRate: currentResult.sampleRate),
        );

        await _audioPlayer!.play();

        // Wait for next chunk synthesis to complete (if started)
        if (nextChunkFuture != null) {
          currentResult = await nextChunkFuture;
          AICOLog.info('🎤 Chunk ${i + 2} pre-synthesized in ${currentResult.synthesisTime.inMilliseconds}ms during playback');
        }

        // Wait for playback to complete
        await _audioPlayer!.playerStateStream.firstWhere(
          (state) => state.processingState == ProcessingState.completed,
        );

        // Update progress
        final progress = (i + 1) / chunks.length;
        _updateState(_currentState.copyWith(progress: progress));
      }

      AICOLog.info('🎤 All chunks completed, returning to idle');
      _updateState(_currentState.copyWith(
        status: TtsStatus.idle,
        currentText: null,
        progress: 1.0,
      ));
    } catch (e, stackTrace) {
      AICOLog.error('TTS synthesis/playback failed', error: e, stackTrace: stackTrace);
      debugPrint('🔴 [TTS] SYNTHESIS ERROR: ${e.toString()}');
      debugPrint('🔴 [TTS] ERROR TYPE: ${e.runtimeType}');
      debugPrint('🔴 [TTS] STACK TRACE:\n$stackTrace');
      _isAvailable = false; // Disable for session
      _updateState(_currentState.copyWith(
        status: TtsStatus.error,
        errorMessage: 'Voice synthesis failed: ${e.toString()}',
      ));
    }
  }


  /// Split text into chunks at sentence boundaries to avoid phoneme limit
  List<String> _splitTextIntoChunks(String text, {int maxChars = 300}) {
    final chunks = <String>[];
    final sentences = text.split(RegExp(r'[.!?]\s+'));
    
    String currentChunk = '';
    for (final sentence in sentences) {
      if (sentence.trim().isEmpty) continue;
      
      final sentenceWithPunctuation = sentence.trim() + '. ';
      
      if (currentChunk.isEmpty) {
        currentChunk = sentenceWithPunctuation;
      } else if ((currentChunk.length + sentenceWithPunctuation.length) <= maxChars) {
        currentChunk += sentenceWithPunctuation;
      } else {
        // Current chunk is full, save it and start new one
        chunks.add(currentChunk.trim());
        currentChunk = sentenceWithPunctuation;
      }
    }
    
    // Add remaining chunk
    if (currentChunk.isNotEmpty) {
      chunks.add(currentChunk.trim());
    }
    
    return chunks.isEmpty ? [text] : chunks;
  }

  @override
  Future<void> stop() async {
    if (!_isAvailable) return;

    try {
      // Stop audio playback
      if (_audioPlayer != null) {
        await _audioPlayer!.stop();
      }
      
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
    if (_isDisposed) {
      AICOLog.warn('Attempted to update state after disposal');
      return;
    }
    _currentState = newState;
    if (!_stateController.isClosed) {
      _stateController.add(newState);
    }
  }

  /// Convert audio samples to WAV format (just_audio requires a container format)
  Uint8List _convertToWav(List<num> samples, int sampleRate) {
    final pcmData = _convertToPCM16(samples);
    return _createWavFile(pcmData, sampleRate);
  }

  /// Convert audio samples to PCM16 bytes
  Uint8List _convertToPCM16(List<num> samples) {
    final bytes = Uint8List(samples.length * 2);
    for (int i = 0; i < samples.length; i++) {
      // Clamp to [-1.0, 1.0] and convert to 16-bit PCM
      final sample = (samples[i].toDouble().clamp(-1.0, 1.0) * 32767).round();
      bytes[i * 2] = sample & 0xFF;
      bytes[i * 2 + 1] = (sample >> 8) & 0xFF;
    }
    return bytes;
  }

  /// Create a WAV file header + PCM data
  Uint8List _createWavFile(Uint8List pcmData, int sampleRate) {
    final dataSize = pcmData.length;
    final fileSize = 36 + dataSize;
    
    final wav = ByteData(44 + dataSize);
    
    // RIFF header
    wav.setUint8(0, 0x52); // 'R'
    wav.setUint8(1, 0x49); // 'I'
    wav.setUint8(2, 0x46); // 'F'
    wav.setUint8(3, 0x46); // 'F'
    wav.setUint32(4, fileSize, Endian.little);
    wav.setUint8(8, 0x57);  // 'W'
    wav.setUint8(9, 0x41);  // 'A'
    wav.setUint8(10, 0x56); // 'V'
    wav.setUint8(11, 0x45); // 'E'
    
    // fmt chunk
    wav.setUint8(12, 0x66); // 'f'
    wav.setUint8(13, 0x6D); // 'm'
    wav.setUint8(14, 0x74); // 't'
    wav.setUint8(15, 0x20); // ' '
    wav.setUint32(16, 16, Endian.little); // fmt chunk size
    wav.setUint16(20, 1, Endian.little);  // audio format (1 = PCM)
    wav.setUint16(22, 1, Endian.little);  // num channels (1 = mono)
    wav.setUint32(24, sampleRate, Endian.little); // sample rate
    wav.setUint32(28, sampleRate * 2, Endian.little); // byte rate
    wav.setUint16(32, 2, Endian.little);  // block align
    wav.setUint16(34, 16, Endian.little); // bits per sample
    
    // data chunk
    wav.setUint8(36, 0x64); // 'd'
    wav.setUint8(37, 0x61); // 'a'
    wav.setUint8(38, 0x74); // 't'
    wav.setUint8(39, 0x61); // 'a'
    wav.setUint32(40, dataSize, Endian.little);
    
    // Copy PCM data
    final wavBytes = wav.buffer.asUint8List();
    wavBytes.setRange(44, 44 + dataSize, pcmData);
    
    return wavBytes;
  }

  @override
  Future<void> dispose() async {
    if (_isDisposed) return;
    _isDisposed = true;
    
    // Dispose audio player
    await _audioPlayer?.dispose();
    
    // Dispose isolate service (kills background isolate)
    await _isolateService?.dispose();
    
    if (!_stateController.isClosed) {
      await _stateController.close();
    }
  }
}

/// Custom audio source for WAV data
class _RawAudioSource extends StreamAudioSource {
  final Uint8List _audioBytes;
  final int sampleRate;

  _RawAudioSource(this._audioBytes, {required this.sampleRate});

  @override
  Future<StreamAudioResponse> request([int? start, int? end]) async {
    start ??= 0;
    end ??= _audioBytes.length;
    
    return StreamAudioResponse(
      sourceLength: _audioBytes.length,
      contentLength: end - start,
      offset: start,
      stream: Stream.value(_audioBytes.sublist(start, end)),
      contentType: 'audio/wav',
    );
  }
}
