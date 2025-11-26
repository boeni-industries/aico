import 'dart:async';
import 'dart:collection';
import 'dart:typed_data';

import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/data/datasources/remote/tts_remote_datasource.dart';
import 'package:aico_frontend/domain/entities/tts_state.dart';
import 'package:aico_frontend/domain/repositories/tts_repository.dart';
import 'package:just_audio/just_audio.dart';
import 'package:crypto/crypto.dart';
import 'dart:convert';
import 'package:flutter/foundation.dart';

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
  final _audioCache = LinkedHashMap<String, Uint8List>();
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
        
        // Set status to preparing (NOT speaking yet)
        _updateState(_currentState.copyWith(
          status: TtsStatus.initializing,
          currentText: text,
          progress: 0.0,
        ));
        
        // Collect raw PCM chunks
        final pcmBuffer = <int>[];
        int chunkCount = 0;
        
        await for (final chunk in _remoteDataSource.synthesize(
          text: text,
          language: 'en', // TODO: Get from user preferences
          speed: 1.0,
        )) {
          chunkCount++;
          pcmBuffer.addAll(chunk);
          AICOLog.info('📦 Chunk $chunkCount: ${chunk.length} bytes PCM data');
        }
        
        if (pcmBuffer.isEmpty) {
          throw Exception('No audio data received from backend');
        }
        
        AICOLog.info('✅ Received $chunkCount chunks, total ${pcmBuffer.length} bytes PCM data');
        
        // Add WAV header to raw PCM data
        wavData = _addWavHeader(Uint8List.fromList(pcmBuffer), sampleRate: 22050, channels: 1);
        
        // Add to cache
        _addToCache(cacheKey, wavData);
      }
      
      // Set up audio source first
      await _audioPlayer?.setAudioSource(
        _BytesAudioSource(wavData),
      );
      
      // Set up completion listener - SIMPLE: just wait for completed state
      _audioStreamSubscription?.cancel();
      _audioStreamSubscription = _audioPlayer?.playerStateStream.listen((playerState) {
        debugPrint('🎵 [TTS] Player state: ${playerState.processingState}, playing: ${playerState.playing}');
        
        // When playback completes, return to idle
        if (playerState.processingState == ProcessingState.completed) {
          debugPrint('🎵 [TTS] ✅ Playback completed - returning to idle');
          _updateState(_currentState.copyWith(
            status: TtsStatus.idle,
            currentText: null,
            progress: 1.0,
          ));
        }
      });
      
      // NOW set status to speaking and start playback
      debugPrint('🎵 [TTS] Setting status to SPEAKING');
      _updateState(_currentState.copyWith(
        status: TtsStatus.speaking,
        currentText: text,
        progress: 0.0,
      ));
      
      // Start playback
      await _audioPlayer?.play();
      debugPrint('🎵 [TTS] Playback started');
      
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

  /// Add WAV header to raw PCM data
  Uint8List _addWavHeader(Uint8List pcmData, {required int sampleRate, required int channels}) {
    final int byteRate = sampleRate * channels * 2; // 16-bit = 2 bytes per sample
    final int dataSize = pcmData.length;
    final int fileSize = 36 + dataSize;
    
    final header = ByteData(44);
    
    // RIFF header
    header.setUint8(0, 0x52); // 'R'
    header.setUint8(1, 0x49); // 'I'
    header.setUint8(2, 0x46); // 'F'
    header.setUint8(3, 0x46); // 'F'
    header.setUint32(4, fileSize, Endian.little);
    
    // WAVE header
    header.setUint8(8, 0x57);  // 'W'
    header.setUint8(9, 0x41);  // 'A'
    header.setUint8(10, 0x56); // 'V'
    header.setUint8(11, 0x45); // 'E'
    
    // fmt subchunk
    header.setUint8(12, 0x66); // 'f'
    header.setUint8(13, 0x6D); // 'm'
    header.setUint8(14, 0x74); // 't'
    header.setUint8(15, 0x20); // ' '
    header.setUint32(16, 16, Endian.little); // Subchunk1Size (16 for PCM)
    header.setUint16(20, 1, Endian.little);  // AudioFormat (1 = PCM)
    header.setUint16(22, channels, Endian.little);
    header.setUint32(24, sampleRate, Endian.little);
    header.setUint32(28, byteRate, Endian.little);
    header.setUint16(32, channels * 2, Endian.little); // BlockAlign
    header.setUint16(34, 16, Endian.little); // BitsPerSample
    
    // data subchunk
    header.setUint8(36, 0x64); // 'd'
    header.setUint8(37, 0x61); // 'a'
    header.setUint8(38, 0x74); // 't'
    header.setUint8(39, 0x61); // 'a'
    header.setUint32(40, dataSize, Endian.little);
    
    // Combine header + PCM data
    final result = Uint8List(44 + dataSize);
    result.setRange(0, 44, header.buffer.asUint8List());
    result.setRange(44, 44 + dataSize, pcmData);
    
    return result;
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
