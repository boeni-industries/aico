import 'dart:async';
import 'dart:typed_data';

import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/data/datasources/remote/tts_remote_datasource.dart';
import 'package:aico_frontend/domain/entities/tts_state.dart';
import 'package:aico_frontend/domain/repositories/tts_repository.dart';
import 'package:just_audio/just_audio.dart';

/// TTS repository implementation with backend streaming
class TtsRepositoryImpl implements TtsRepository {
  final TtsRemoteDataSource _remoteDataSource;
  final _stateController = StreamController<TtsState>.broadcast();
  TtsState _currentState = TtsState.initial();
  bool _isDisposed = false;

  AudioPlayer? _audioPlayer;
  bool _isAvailable = false;
  StreamSubscription? _audioStreamSubscription;

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
      _updateState(_currentState.copyWith(
        status: TtsStatus.speaking,
        currentText: text,
        progress: 0.0,
      ));
      
      AICOLog.info('🎤 Requesting TTS from backend: ${text.length} chars');
      
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
      final wavData = _addWavHeader(Uint8List.fromList(pcmBuffer), sampleRate: 22050, channels: 1);
      
      // Play the audio using just_audio
      await _audioPlayer?.setAudioSource(
        _BytesAudioSource(wavData),
      );
      
      // Listen to player state changes
      _audioStreamSubscription = _audioPlayer?.playerStateStream.listen((state) {
        if (state.processingState == ProcessingState.completed) {
          _updateState(_currentState.copyWith(
            status: TtsStatus.idle,
            currentText: null,
            progress: 1.0,
          ));
        }
      });
      
      await _audioPlayer?.play();
      
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
