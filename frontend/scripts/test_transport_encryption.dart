import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:sodium/sodium.dart';
import 'package:sodium_libs/sodium_libs.dart' as sodium_libs;

void main() {
  runApp(const EncryptionTestApp());
}

class EncryptionTestApp extends StatelessWidget {
  const EncryptionTestApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Encryption Test',
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: const EncryptionTestScreen(),
    );
  }
}

class EncryptionTestScreen extends StatefulWidget {
  const EncryptionTestScreen({super.key});

  @override
  _EncryptionTestScreenState createState() => _EncryptionTestScreenState();
}

class _EncryptionTestScreenState extends State<EncryptionTestScreen> {
  String _logOutput = 'Initializing...\n';
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    // Run encryption tests
    _runTests();
  }

  void _log(String message) {
    // ignore: avoid_print
    debugPrint(message);
    if (!mounted) return;
    setState(() {
      _logOutput += '$message\n';
    });
    // Scroll to the bottom
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
      }
    });
  }

  Future<void> _runTests() async {
    _log('🚀 AICO Transport Encryption Test (Flutter + libsodium)');
    _log('=' * 50);

    try {
      // Initialize sodium using the flutter-specific implementation
      final sodium = await sodium_libs.SodiumInit.init();
      _log('✅ Sodium initialized');

      final success = await runFullTest(sodium, _log);
      _log(success
          ? '🎉 TEST SUITE COMPLETED SUCCESSFULLY!'
          : '❌ TEST SUITE FAILED');
    } catch (e) {
      _log('\n❌ Unexpected error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Libsodium Encryption Test'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(8.0),
        child: SingleChildScrollView(
          controller: _scrollController,
          child: SelectableText(
            _logOutput,
            style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
          ),
        ),
      ),
    );
  }
}

/// Main test runner
Future<bool> runFullTest(Sodium sodium, void Function(String) log) async {
  // Test 1: Backend connectivity
  const baseUrl = 'http://127.0.0.1:8771';
  if (!await testBackendConnectivity(baseUrl, log)) {
    log('\n❌ Backend connectivity test failed');
    log('Make sure the AICO backend is running with: aico gateway start');
    return false;
  }

  // Test 2: Encrypted handshake and communication
  log('\n🔐 Testing encrypted communication with libsodium...');

  final client = TransportEncryptionTestClient(baseUrl, sodium, log);

  // Perform handshake
  if (!await client.performHandshake()) {
    log('\n❌ Encrypted handshake test failed');
    return false;
  }

  // Test encrypted echo
  log('\n📡 Testing encrypted echo...');
  final echoResponse = await client.sendEncryptedRequest('/api/v1/echo/', {
    'message': 'Hello from encrypted Dart client!',
    'test_data': {
      'encryption': 'XChaCha20-Poly1305',
      'identity': 'Ed25519',
      'timestamp': DateTime.now().millisecondsSinceEpoch ~/ 1000,
    }
  });

  bool echoSuccess = false;
  if (echoResponse != null) {
    log('✅ Encrypted echo successful');
    log('Echo response: ${jsonEncode(echoResponse)}');
    echoSuccess = true;
  } else {
    log('❌ Encrypted echo test failed');
  }

  log('\n${'=' * 50}');

  if (echoSuccess) {
    log('🎉 Transport Encryption Test COMPLETED SUCCESSFULLY!');
    log('\n✅ All tests passed:');
    log('  • Backend connectivity');
    log('  • Encrypted handshake protocol');
    log('  • Encrypted echo test');
    log('\n🔐 Dart-backend encryption is working correctly!');
    return true;
  } else {
    log('⚠️ Transport Encryption Test FAILED');
    log('\n✅ Passed tests:');
    log('  • Backend connectivity');
    log('  • Encrypted handshake protocol');
    log('\n❌ Failed tests:');
    log('  • Encrypted echo endpoint');
    log('\n🔧 The handshake succeeded, but the encrypted echo test failed.');
    return false;
  }
}

/// Test basic backend connectivity
Future<bool> testBackendConnectivity(String baseUrl, void Function(String) log) async {
  log('🌐 Testing backend connectivity at $baseUrl');

  final dio = Dio();

  // Try multiple possible health endpoints
  final endpointsToTry = [
    '$baseUrl/api/v1/gateway/status',
    '$baseUrl/api/v1/health',
    '$baseUrl/health',
  ];

  for (final endpoint in endpointsToTry) {
    try {
      final response = await dio.get(
        endpoint,
        options: Options(
          sendTimeout: const Duration(seconds: 5),
          receiveTimeout: const Duration(seconds: 5),
        ),
      );

      if (response.statusCode == 200) {
        log('✅ Backend is responding at $endpoint');
        return true;
      } else {
        log('⚠️ $endpoint returned HTTP ${response.statusCode}');
      }
    } catch (e) {
      log('⚠️ $endpoint failed: $e');
      continue;
    }
  }

  log('❌ No working health endpoints found');
  return false;
}

/// Transport encryption test client with real libsodium
class TransportEncryptionTestClient {
  final String baseUrl;
  final String handshakeUrl;
  final Dio _dio;
  final Sodium _sodium;
  final void Function(String) _log;

  // Client identity (Ed25519 keypair)
  late final KeyPair _signingKeyPair;
  late final KeyPair _ephemeralKeyPair;

  // Session state
  KeyPair? _sessionKeyPair; // Ephemeral X25519 keypair for the session
  Uint8List? _serverPublicKey;

  TransportEncryptionTestClient(this.baseUrl, this._sodium, this._log)
      : handshakeUrl = '$baseUrl/api/v1/handshake',
        _dio = Dio() {
    _generateClientIdentity();
    final publicKeyBytes = _signingKeyPair.publicKey;
    _log(
        '🔑 Client identity generated: ${publicKeyBytes.take(8).map((b) => b.toRadixString(16).padLeft(2, '0')).join()}...');
  }

  /// Generate client Ed25519 identity using libsodium
  void _generateClientIdentity() {
    _signingKeyPair = _sodium.crypto.sign.keyPair();
    _ephemeralKeyPair = _sodium.crypto.kx.keyPair();
  }

  /// Perform encrypted handshake with backend
  Future<bool> performHandshake() async {
    _log('\n🤝 Starting encrypted handshake...');

    try {
      // Step 1: Generate ephemeral X25519 keypair for session
      final clientPrivateKey = _ephemeralKeyPair.secretKey;
      final clientPublicKey = _ephemeralKeyPair.publicKey;

      // Step 2: Create handshake request
      final challengeBytes = _sodium.randombytes.buf(32);
      final handshakeRequest = {
        'component': 'dart_test_client',
        'identity_key': base64Encode(_signingKeyPair.publicKey),
        'public_key': base64Encode(clientPublicKey),
        'timestamp': DateTime.now().millisecondsSinceEpoch ~/ 1000,
        'challenge': base64Encode(challengeBytes),
      };

      // Step 3: Create Ed25519 signature
      final signature = _sodium.crypto.sign.detached(
        message: challengeBytes,
        secretKey: _signingKeyPair.secretKey,
      );
      handshakeRequest['signature'] = base64Encode(signature);

      final handshakePayload = {
        'handshake_request': handshakeRequest,
      };

      _log('📤 Sending handshake request...');

      // Step 4: Send handshake request
      final response = await _dio.post(
        handshakeUrl,
        data: handshakePayload,
        options: Options(
          headers: {'Content-Type': 'application/json'},
          sendTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 10),
        ),
      );

      if (response.statusCode != 200) {
        _log('❌ Handshake failed: HTTP ${response.statusCode}');
        _log('Response: ${response.data}');
        return false;
      }

      // Step 5: Process handshake response
      final handshakeResponse = response.data as Map<String, dynamic>;

      if (handshakeResponse['status'] != 'session_established') {
        _log(
            '❌ Handshake rejected: ${handshakeResponse['error'] ?? 'Unknown error'}');
        return false;
      }

      // Step 6: Extract server public key and derive session key
      final responseData =
          handshakeResponse['handshake_response'] as Map<String, dynamic>;
      final serverPublicKeyB64 = responseData['public_key'] as String;
      _serverPublicKey = base64Decode(serverPublicKeyB64);

      // Step 7: Store the ephemeral keypair for this session
      _sessionKeyPair = KeyPair(publicKey: clientPublicKey, secretKey: clientPrivateKey);

      _log('✅ Handshake completed successfully!');
      _log(
          '🔐 Session established with server public key: ${base64Encode(_serverPublicKey!).substring(0, 12)}...');

      return true;
    } catch (e) {
      _log('❌ Handshake error: $e');
      return false;
    }
  }

  /// Encrypt message using crypto_box (XChaCha20-Poly1305 with key exchange)
  String encryptMessage(Map<String, dynamic> payload) {
    if (_sessionKeyPair == null || _serverPublicKey == null) {
      throw StateError('No active session - perform handshake first');
    }

    // Serialize payload
    final plaintext = utf8.encode(jsonEncode(payload));

    // Generate nonce for crypto_box
    final nonce = _sodium.randombytes.buf(_sodium.crypto.box.nonceBytes);

    // Encrypt using the client's private key and server's public key
    final cipherText = _sodium.crypto.box.easy(
      message: plaintext,
      nonce: nonce,
      publicKey: _serverPublicKey!,
      secretKey: _sessionKeyPair!.secretKey,
    );

    return base64Encode([...nonce, ...cipherText]);
  }

  /// Decrypt message using crypto_box
  Map<String, dynamic> decryptMessage(String encryptedB64) {
    if (_sessionKeyPair == null || _serverPublicKey == null) {
      throw StateError('No active session - perform handshake first');
    }

    // Decode the encrypted message
    final encrypted = base64Decode(encryptedB64);
    final nonceBytes = _sodium.crypto.box.nonceBytes;
    final nonce = encrypted.sublist(0, nonceBytes);
    final cipherText = encrypted.sublist(nonceBytes);

    // Decrypt using the server's public key and client's private key
    final decrypted = _sodium.crypto.box.openEasy(
      cipherText: cipherText,
      nonce: nonce,
      publicKey: _serverPublicKey!,
      secretKey: _sessionKeyPair!.secretKey,
    );

    // Parse JSON
    final plaintext = utf8.decode(decrypted);
    return jsonDecode(plaintext) as Map<String, dynamic>;
  }

  /// Send encrypted request to backend
  Future<Map<String, dynamic>?> sendEncryptedRequest(
    String endpoint,
    Map<String, dynamic> payload,
  ) async {
    if (_sessionKeyPair == null) {
      _log('❌ No active session - perform handshake first');
      return null;
    }

    try {
      // Encrypt the payload
      final encryptedPayload = encryptMessage(payload);

      // Create encrypted request envelope
      final publicKeyBytes = _signingKeyPair.publicKey;
      final requestEnvelope = {
        'encrypted': true,
        'payload': encryptedPayload,
        'client_id': publicKeyBytes
            .take(8)
            .map((b) => b.toRadixString(16).padLeft(2, '0'))
            .join(),
      };

      _log('📤 Sending encrypted request to $endpoint');

      // Send request
      final response = await _dio.post(
        '$baseUrl$endpoint',
        data: requestEnvelope,
        options: Options(
          headers: {'Content-Type': 'application/json'},
          sendTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 10),
        ),
      );

      if (response.statusCode != 200) {
        _log('❌ Request failed: HTTP ${response.statusCode}');
        _log('Response: ${response.data}');
        return null;
      }

      // Process response
      final responseData = response.data as Map<String, dynamic>;

      if (responseData['encrypted'] == true) {
        // Decrypt response
        final decryptedResponse =
            decryptMessage(responseData['payload'] as String);
        _log('✅ Received encrypted response');
        return decryptedResponse;
      } else {
        _log('✅ Received plaintext response');
        return responseData;
      }
    } catch (e) {
      _log('❌ Encryption/network error: $e');
      return null;
    }
  }
}
