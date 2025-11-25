import 'dart:async';
import 'dart:isolate';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:kokoro_tts_flutter/kokoro_tts_flutter.dart';
import 'package:aico_frontend/core/logging/aico_log.dart';

/// Data passed to the isolate on initialization
class TtsIsolateInitData {
  final SendPort sendPort;
  final RootIsolateToken rootIsolateToken;
  final String modelPath;
  final String voicesPath;

  TtsIsolateInitData({
    required this.sendPort,
    required this.rootIsolateToken,
    required this.modelPath,
    required this.voicesPath,
  });
}

/// Request to synthesize TTS
class TtsSynthesisRequest {
  final String id;
  final String text;
  final String voice;
  final double speed;

  TtsSynthesisRequest({
    required this.id,
    required this.text,
    required this.voice,
    required this.speed,
  });
}

/// Result of TTS synthesis
class TtsSynthesisResult {
  final String id;
  final List<double> audioSamples;
  final int sampleRate;
  final Duration synthesisTime;

  TtsSynthesisResult({
    required this.id,
    required this.audioSamples,
    required this.sampleRate,
    required this.synthesisTime,
  });
}

/// Error from TTS synthesis
class TtsSynthesisError {
  final String id;
  final String message;

  TtsSynthesisError({
    required this.id,
    required this.message,
  });
}

/// Service that manages TTS synthesis in a background isolate
class TtsIsolateService {
  Isolate? _isolate;
  SendPort? _sendPort;
  ReceivePort? _receivePort;
  final _pendingRequests = <String, Completer<TtsSynthesisResult>>{};
  bool _isInitialized = false;

  final String modelPath;
  final String voicesPath;

  TtsIsolateService({
    this.modelPath = 'assets/tts/kokoro-v1.0.onnx',
    this.voicesPath = 'assets/tts/voices.json',
  });

  /// Initialize the isolate
  Future<void> initialize() async {
    if (_isInitialized) {
      AICOLog.warn('TTS isolate already initialized');
      return;
    }

    AICOLog.info('🔧 Initializing TTS isolate...');

    // Get the root isolate token
    final rootIsolateToken = RootIsolateToken.instance!;

    // Create receive port for main isolate
    _receivePort = ReceivePort();

    // Spawn the isolate
    _isolate = await Isolate.spawn(
      _isolateEntry,
      TtsIsolateInitData(
        sendPort: _receivePort!.sendPort,
        rootIsolateToken: rootIsolateToken,
        modelPath: modelPath,
        voicesPath: voicesPath,
      ),
    );

    // Create a completer to wait for isolate initialization
    final initCompleter = Completer<void>();

    // Listen for messages from isolate
    _receivePort!.listen((message) {
      if (message is SendPort) {
        // First message is the isolate's SendPort
        _sendPort = message;
        _isInitialized = true;
        AICOLog.info('✅ TTS isolate initialized');
        if (!initCompleter.isCompleted) {
          initCompleter.complete();
        }
      } else if (message is TtsSynthesisResult) {
        // Synthesis completed successfully
        final completer = _pendingRequests.remove(message.id);
        completer?.complete(message);
      } else if (message is TtsSynthesisError) {
        // Synthesis failed
        final completer = _pendingRequests.remove(message.id);
        completer?.completeError(Exception(message.message));
      }
    });

    // Wait for isolate to send its SendPort (with timeout)
    await initCompleter.future.timeout(
      const Duration(seconds: 5),
      onTimeout: () {
        throw Exception('TTS isolate initialization timed out');
      },
    );
  }

  /// Synthesize TTS audio
  Future<TtsSynthesisResult> synthesize(TtsSynthesisRequest request) async {
    if (!_isInitialized || _sendPort == null) {
      throw Exception('TTS isolate not initialized');
    }

    final completer = Completer<TtsSynthesisResult>();
    _pendingRequests[request.id] = completer;

    // Send request to isolate
    _sendPort!.send(request);

    return completer.future;
  }

  /// Dispose the isolate
  Future<void> dispose() async {
    if (_isolate != null) {
      _isolate!.kill(priority: Isolate.immediate);
      _isolate = null;
    }
    _receivePort?.close();
    _sendPort = null;
    _isInitialized = false;
    _pendingRequests.clear();
    AICOLog.info('🔴 TTS isolate disposed');
  }

  /// Isolate entry point
  static void _isolateEntry(TtsIsolateInitData initData) {
    _isolateEntryAsync(initData);
  }

  static Future<void> _isolateEntryAsync(TtsIsolateInitData initData) async {
    final receivePort = ReceivePort();
    Kokoro? kokoro;

    try {
      debugPrint('[TTS_ISOLATE] Starting isolate initialization...');
      
      // CRITICAL: Initialize BackgroundIsolateBinaryMessenger to enable platform plugins
      BackgroundIsolateBinaryMessenger.ensureInitialized(initData.rootIsolateToken);
      debugPrint('[TTS_ISOLATE] BackgroundIsolateBinaryMessenger initialized');

      // Send our SendPort back to main isolate
      initData.sendPort.send(receivePort.sendPort);
      debugPrint('[TTS_ISOLATE] SendPort sent to main isolate');

      // Initialize Kokoro TTS
      debugPrint('[TTS_ISOLATE] Creating Kokoro config...');
      final config = KokoroConfig(
        modelPath: initData.modelPath,
        voicesPath: initData.voicesPath,
      );
      debugPrint('[TTS_ISOLATE] Initializing Kokoro...');
      kokoro = Kokoro(config);
      await kokoro.initialize();
      debugPrint('[TTS_ISOLATE] ✅ Kokoro initialized successfully');

      // Listen for synthesis requests
      debugPrint('[TTS_ISOLATE] Ready to receive synthesis requests');
      await for (final message in receivePort) {
        if (message is TtsSynthesisRequest) {
          try {
            debugPrint('[TTS_ISOLATE] Received synthesis request: ${message.id}');
            debugPrint('[TTS_ISOLATE] Text length: ${message.text.length}, Voice: ${message.voice}');
            final startTime = DateTime.now();

            // Perform synthesis
            debugPrint('[TTS_ISOLATE] Starting Kokoro synthesis...');
            final result = await kokoro.createTTS(
              text: message.text,
              voice: message.voice,
              speed: message.speed,
            );
            debugPrint('[TTS_ISOLATE] Synthesis complete, audio samples: ${result.audio.length}');

            final synthesisTime = DateTime.now().difference(startTime);

            // Send result back
            debugPrint('[TTS_ISOLATE] Sending result back to main isolate...');
            initData.sendPort.send(TtsSynthesisResult(
              id: message.id,
              audioSamples: result.audio.map((e) => e.toDouble()).toList(),
              sampleRate: result.sampleRate,
              synthesisTime: synthesisTime,
            ));
            debugPrint('[TTS_ISOLATE] ✅ Result sent successfully');
          } catch (e, stackTrace) {
            // Send error back
            debugPrint('[TTS_ISOLATE] ❌ Synthesis error: $e');
            debugPrint('[TTS_ISOLATE] Stack trace: $stackTrace');
            initData.sendPort.send(TtsSynthesisError(
              id: message.id,
              message: e.toString(),
            ));
          }
        }
      }
    } catch (e) {
      initData.sendPort.send(TtsSynthesisError(
        id: 'init',
        message: 'Failed to initialize TTS isolate: $e',
      ));
    } finally {
      kokoro?.dispose();
      receivePort.close();
    }
  }
}
