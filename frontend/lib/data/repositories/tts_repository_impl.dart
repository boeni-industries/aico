import 'dart:async';
import 'dart:convert';

import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/data/datasources/remote/tts_remote_datasource.dart';
import 'package:aico_frontend/domain/entities/tts_state.dart';
import 'package:aico_frontend/domain/repositories/tts_repository.dart';
import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';

/// TTS repository implementation with backend streaming and LRU cache
class TtsRepositoryImpl implements TtsRepository {
  final TtsRemoteDataSource _remoteDataSource;
  final _stateController = StreamController<TtsState>.broadcast();
  TtsState _currentState = TtsState.initial();
  bool _isDisposed = false;

  AudioPlayer? _audioPlayer;
  bool _isAvailable = false;
  StreamSubscription? _audioStreamSubscription;

  // LRU cache for audio data (text hash -> WAV bytes)
  final Map<String, Uint8List> _audioCache = <String, Uint8List>{};
  static const int _maxCacheSize = 20; // Max 20 cached audio files
  static const int _maxCacheBytes = 50 * 1024 * 1024; // 50MB max
  int _currentCacheBytes = 0;

  TtsRepositoryImpl(this._remoteDataSource);

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
        engine: TtsEngine.backend,
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
      // Generate cache key from text
      final cacheKey = _generateCacheKey(text);
      
      // Check cache first
      Uint8List? wavData = _audioCache[cacheKey];
      
      if (wavData != null) {
        AICOLog.info('🎯 Cache HIT for text (${text.length} chars)');
        // Move to end (most recently used)
        _audioCache.remove(cacheKey);
        _audioCache[cacheKey] = wavData;
      } else {
        AICOLog.info('🎤 Cache MISS - Requesting TTS from backend: ${text.length} chars');
        
        // Set status to preparing
        _updateState(_currentState.copyWith(
          status: TtsStatus.initializing,
          currentText: text,
          progress: 0.0,
        ));
        
        // Buffer all chunks (backend sends single progressive WAV: header + PCM chunks)
        // Progressive playback with just_audio requires complex handling - buffer for reliability
        final pcmBuffer = <int>[];
        int chunkCount = 0;
        
        await for (final chunk in _remoteDataSource.synthesize(
          text: text,
          language: 'en',
          speed: 1.0,
        )) {
          chunkCount++;
          pcmBuffer.addAll(chunk);
          AICOLog.debug('📦 Chunk $chunkCount: ${chunk.length} bytes');
        }
        
        AICOLog.info('✅ Received $chunkCount chunks, total ${pcmBuffer.length} bytes');
        wavData = Uint8List.fromList(pcmBuffer);
        
        // Cache the audio
        _addToCache(cacheKey, wavData);
      }
      
      // For cached audio, set up and play normally
      await _audioPlayer?.setAudioSource(_BytesAudioSource(wavData));
      
      _audioStreamSubscription?.cancel();
      _audioStreamSubscription = _audioPlayer?.playerStateStream.listen((playerState) async {
        if (playerState.processingState == ProcessingState.completed) {
          await _audioPlayer?.pause();
          await _audioPlayer?.seek(Duration.zero);
          _updateState(_currentState.copyWith(
            status: TtsStatus.idle,
            currentText: null,
          ));
        }
      });
      
      _updateState(_currentState.copyWith(
        status: TtsStatus.speaking,
        currentText: text,
        metadata: {'audioData': base64.encode(wavData)},
      ));
      
      debugPrint('🎵 [TTS] Audio passed to WebView (cached)');
      
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

  /// Generate cache key from text (SHA256 hash)
  String _generateCacheKey(String text) {
    final bytes = utf8.encode(text.trim().toLowerCase());
    final digest = sha256.convert(bytes);
    return digest.toString();
  }

  /// Add audio to cache with LRU eviction
  void _addToCache(String key, Uint8List data) {
    final dataSize = data.length;
    
    // Evict oldest entries if cache is full
    while (_audioCache.length >= _maxCacheSize || 
           (_currentCacheBytes + dataSize) > _maxCacheBytes) {
      if (_audioCache.isEmpty) break;
      
      final oldestKey = _audioCache.keys.first;
      final oldestData = _audioCache.remove(oldestKey);
      if (oldestData != null) {
        _currentCacheBytes -= oldestData.length;
        AICOLog.info('🗑️ Evicted cache entry (${oldestData.length} bytes)');
      }
    }
    
    // Add new entry
    _audioCache[key] = data;
    _currentCacheBytes += dataSize;
    AICOLog.info('💾 Cached audio: ${_audioCache.length} entries, ${(_currentCacheBytes / 1024 / 1024).toStringAsFixed(1)}MB');
  }

  @override
  Future<void> dispose() async {
    if (_isDisposed) return;
    _isDisposed = true;
    await _audioStreamSubscription?.cancel();
    await _audioPlayer?.dispose();
    if (!_stateController.isClosed) {
      await _stateController.close();
    }
  }
}

/// Custom audio source for playing bytes with just_audio
class _BytesAudioSource extends StreamAudioSource {
  final Uint8List _bytes;

  _BytesAudioSource(this._bytes);

  @override
  Future<StreamAudioResponse> request([int? start, int? end]) async {
    start ??= 0;
    end ??= _bytes.length;
    return StreamAudioResponse(
      sourceLength: _bytes.length,
      contentLength: end - start,
      offset: start,
      stream: Stream.value(_bytes.sublist(start, end)),
      contentType: 'audio/wav',
    );
  }
}

/// Progressive audio source for streaming playback
/// Buffers incoming chunks and serves them to the audio player as requested
class _ProgressiveAudioSource extends StreamAudioSource {
  final Stream<Uint8List> _dataStream;
  final List<int> _buffer = [];
  final Completer<void> _completionCompleter = Completer<void>();
  bool _streamComplete = false;
  StreamSubscription? _subscription;

  _ProgressiveAudioSource(this._dataStream) {
    // Start listening to the stream immediately
    _subscription = _dataStream.listen(
      (chunk) {
        _buffer.addAll(chunk);
        debugPrint('🎵 [ProgressiveAudioSource] Buffered chunk: ${chunk.length} bytes, total: ${_buffer.length}');
      },
      onDone: () {
        _streamComplete = true;
        _completionCompleter.complete();
        debugPrint('🎵 [ProgressiveAudioSource] Stream complete: ${_buffer.length} bytes total');
      },
      onError: (error) {
        _streamComplete = true;
        _completionCompleter.completeError(error);
        debugPrint('🎵 [ProgressiveAudioSource] Stream error: $error');
      },
    );
  }

  @override
  Future<StreamAudioResponse> request([int? start, int? end]) async {
    start ??= 0;
    
    // For the initial request, wait for enough data to start playback
    // Need at least WAV header (44 bytes) + some audio data (32KB minimum)
    const minInitialData = 44 + 32768;
    
    if (start == 0 && _buffer.length < minInitialData && !_streamComplete) {
      debugPrint('🎵 [ProgressiveAudioSource] Waiting for initial data... (${_buffer.length}/$minInitialData bytes)');
      
      // Wait for enough initial data
      while (_buffer.length < minInitialData && !_streamComplete) {
        await Future.delayed(const Duration(milliseconds: 100));
      }
      
      debugPrint('🎵 [ProgressiveAudioSource] Initial data ready: ${_buffer.length} bytes');
    }
    
    // For subsequent requests, wait for requested data or stream completion
    final requestedEnd = end ?? start + 8192;
    while (!_streamComplete && _buffer.length < requestedEnd) {
      await Future.delayed(const Duration(milliseconds: 50));
    }
    
    // Calculate actual end position
    end ??= _buffer.length;
    var actualEnd = end > _buffer.length ? _buffer.length : end;
    
    // CRITICAL: Ensure we return at least the WAV header (44 bytes) for initial requests
    // just_audio needs the full header to validate the audio format
    if (start == 0 && actualEnd < 44 && _buffer.length >= 44) {
      actualEnd = 44;
      debugPrint('🎵 [ProgressiveAudioSource] Forcing minimum header size: 44 bytes');
    }
    
    // Also ensure we return a reasonable chunk size for playback to start
    // Player needs enough data to decode and buffer
    if (start == 0 && actualEnd < 8192 && _buffer.length >= 8192) {
      actualEnd = 8192;
      debugPrint('🎵 [ProgressiveAudioSource] Forcing minimum initial chunk: 8192 bytes');
    }
    
    debugPrint('🎵 [ProgressiveAudioSource] Request: start=$start, end=$end, actualEnd=$actualEnd, bufferSize=${_buffer.length}, complete=$_streamComplete');
    
    return StreamAudioResponse(
      sourceLength: _streamComplete ? _buffer.length : null,
      contentLength: actualEnd - start,
      offset: start,
      stream: Stream.value(Uint8List.fromList(_buffer.sublist(start, actualEnd))),
      contentType: 'audio/wav',
    );
  }
  
  /// Wait for the stream to complete
  Future<void> waitForCompletion() => _completionCompleter.future;
  
  /// Get the complete audio data
  Uint8List getCompleteAudio() => Uint8List.fromList(_buffer);
  
  /// Dispose resources
  Future<void> dispose() async {
    await _subscription?.cancel();
  }
}
