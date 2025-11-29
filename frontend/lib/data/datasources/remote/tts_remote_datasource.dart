import 'dart:async';
import 'dart:typed_data';

import 'package:aico_frontend/networking/services/resilient_api_service.dart';
import 'package:aico_frontend/core/logging/aico_log.dart';

/// Remote data source for TTS synthesis via backend
abstract class TtsRemoteDataSource {
  /// Request TTS synthesis and stream audio chunks
  Stream<Uint8List> synthesize({
    required String text,
    required String language,
    double speed = 1.0,
  });
}

class TtsRemoteDataSourceImpl implements TtsRemoteDataSource {
  final ResilientApiService _resilientApi;

  TtsRemoteDataSourceImpl(this._resilientApi);

  @override
  Stream<Uint8List> synthesize({
    required String text,
    required String language,
    double speed = 1.0,
  }) async* {
    try {
      AICOLog.info('🎤 Requesting TTS synthesis from backend: ${text.length} chars, language: $language');
      
      // Build request data
      final requestData = {
        'text': text,
        'language': language,
        'speed': speed,
      };
      
      // Get the underlying API client for binary streaming
      final apiClient = _resilientApi.apiClient;
      await apiClient.initialize();
      
      // Stream binary audio chunks from backend
      await for (final chunk in apiClient.streamBinary(
        'POST',
        '/tts/synthesize',
        data: requestData,
      )) {
        if (chunk.isNotEmpty) {
          yield Uint8List.fromList(chunk);
        }
      }
      
      AICOLog.info('✅ TTS streaming complete');
      
    } catch (e, stackTrace) {
      AICOLog.error('TTS synthesis request failed', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }
}
