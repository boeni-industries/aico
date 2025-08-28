import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:sodium/sodium.dart';
import 'package:sodium_libs/sodium_libs.dart' as sodium_libs;

/// Encryption service for AICO transport security
/// Full NaCl-compatible implementation using Ed25519/X25519/XChaCha20-Poly1305
class EncryptionService {
  static const String _identityKeyKey = 'aico_identity_private_key';
  static const String _identityPublicKeyKey = 'aico_identity_public_key';
  
  static const FlutterSecureStorage _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );

  // Sodium instance
  Sodium? _sodium;
  
  // Identity keys - persistent Ed25519 keypair
  SecureKey? _identityPrivateKey;
  Uint8List? _identityPublicKey;
  
  // Session keys - ephemeral X25519 keypair
  SecureKey? _sessionPrivateKey;
  Uint8List? _sessionPublicKey;
  Uint8List? _serverPublicKey;
  
  // Shared secret for current session
  SecureKey? _sharedSecret;
  
  // Precalculated box for efficient encryption/decryption
  PrecalculatedBox? _precalculatedBox;
  
  String? _clientId;
  bool _sessionEstablished = false;
  
  /// Initialize encryption service with libsodium
  Future<void> initialize() async {
    // Initialize sodium with platform binaries
    _sodium = await sodium_libs.SodiumInit.init();
    
    await _loadOrGenerateIdentityKeys();
  }
  
  /// Load existing identity keys or generate new ones
  Future<void> _loadOrGenerateIdentityKeys() async {
    try {
      // Try to load existing keys
      final privateKeyHex = await _secureStorage.read(key: _identityKeyKey);
      final publicKeyHex = await _secureStorage.read(key: _identityPublicKeyKey);
      
      if (privateKeyHex != null && publicKeyHex != null) {
        final privateKeyBytes = _hexToBytes(privateKeyHex);
        _identityPrivateKey = _sodium!.secureCopy(privateKeyBytes);
        _identityPublicKey = _hexToBytes(publicKeyHex);
      } else {
        // Generate new identity keypair
        await _generateIdentityKeys();
      }
      
      // Generate client_id from identity public key (first 16 chars of hex)
      _clientId = _bytesToHex(_identityPublicKey!).substring(0, 16);
      
    } catch (e) {
      // If loading fails, generate new keys
      await _generateIdentityKeys();
    }
  }
  
  /// Generate new Ed25519 identity keypair
  Future<void> _generateIdentityKeys() async {
    final keyPair = _sodium!.crypto.sign.keyPair();
    _identityPrivateKey = keyPair.secretKey;
    _identityPublicKey = keyPair.publicKey;
    
    // Store securely
    final privateKeyBytes = _identityPrivateKey!.extractBytes();
    await _secureStorage.write(
      key: _identityKeyKey,
      value: _bytesToHex(privateKeyBytes),
    );
    await _secureStorage.write(
      key: _identityPublicKeyKey,
      value: _bytesToHex(_identityPublicKey!),
    );
    
    // Generate client_id
    _clientId = _bytesToHex(_identityPublicKey!).substring(0, 16);
  }
  
  /// Perform handshake with backend
  Future<Map<String, dynamic>> createHandshakeRequest() async {
    if (_identityPrivateKey == null || _identityPublicKey == null) {
      throw EncryptionException('Identity keys not initialized');
    }
    
    // Generate ephemeral X25519 session keypair
    final sessionKeyPair = _sodium!.crypto.box.keyPair();
    _sessionPrivateKey = sessionKeyPair.secretKey;
    _sessionPublicKey = sessionKeyPair.publicKey;
    
    // Create handshake request matching backend protocol
    final challenge = _sodium!.randombytes.buf(32);
    final timestamp = DateTime.now().millisecondsSinceEpoch / 1000;
    
    final handshakeRequest = {
      'component': 'flutter_client',
      'identity_key': base64Encode(_identityPublicKey!), // Ed25519 for signatures
      'public_key': base64Encode(_sessionPublicKey!),    // X25519 for key exchange
      'timestamp': timestamp,
      'challenge': base64Encode(challenge),
    };
    
    // Sign with Ed25519 identity key
    final signature = _sodium!.crypto.sign.detached(
      message: challenge,
      secretKey: _identityPrivateKey!,
    );
    handshakeRequest['signature'] = base64Encode(signature);
    
    return {
      'handshake_request': handshakeRequest,
    };
  }
  
  /// Process handshake response and establish session
  Future<void> processHandshakeResponse(Map<String, dynamic> response) async {
    if (!response.containsKey('handshake_response')) {
      throw EncryptionException('Invalid handshake response format');
    }
    
    final handshakeResponse = response['handshake_response'];
    if (!handshakeResponse.containsKey('public_key')) {
      throw EncryptionException('Missing server public key in handshake response');
    }
    
    // Get server's X25519 public key and perform key exchange
    _serverPublicKey = base64Decode(handshakeResponse['public_key']);
    
    // Perform X25519 key exchange to derive shared secret  
    // Use the server public key with our session private key
    final precalculatedBox = _sodium!.crypto.box.precalculate(
      publicKey: _serverPublicKey!,
      secretKey: _sessionPrivateKey!,
    );
    // Store the precalculated box for encryption/decryption
    _precalculatedBox = precalculatedBox;
    
    _sessionEstablished = true;
  }
  
  /// Encrypt JSON payload using X25519 + XSalsa20-Poly1305
  String encryptPayload(Map<String, dynamic> payload) {
    if (!_sessionEstablished || _precalculatedBox == null) {
      throw EncryptionException('No active encryption session');
    }
    
    // Convert payload to JSON bytes
    final jsonString = json.encode(payload);
    final plaintext = utf8.encode(jsonString);
    
    // Generate random nonce
    final nonce = _sodium!.randombytes.buf(_sodium!.crypto.box.nonceBytes);
    
    // Encrypt with precalculated box (X25519 + XSalsa20-Poly1305)
    final ciphertext = _precalculatedBox!.easy(
      message: plaintext,
      nonce: nonce,
    );
    
    // Combine nonce + ciphertext and encode as base64 (NaCl format)
    final combined = Uint8List.fromList([...nonce, ...ciphertext]);
    return base64Encode(combined);
  }
  
  /// Create encrypted request envelope
  Map<String, dynamic> createEncryptedRequest(Map<String, dynamic> payload) {
    final encryptedPayload = encryptPayload(payload);
    return {
      'encrypted': true,
      'payload': encryptedPayload,
      'client_id': _clientId,
    };
  }
  
  /// Decrypt response payload using X25519 + XSalsa20-Poly1305
  Map<String, dynamic> decryptPayload(String encryptedPayload) {
    if (!_sessionEstablished || _precalculatedBox == null) {
      throw EncryptionException('No active encryption session');
    }
    
    // Decode base64 combined payload (nonce + ciphertext)
    final combined = base64Decode(encryptedPayload);
    
    // Extract nonce (first 24 bytes) and ciphertext (remaining bytes)
    final nonceBytes = _sodium!.crypto.box.nonceBytes;
    final nonce = combined.sublist(0, nonceBytes);
    final ciphertext = combined.sublist(nonceBytes);
    
    // Decrypt with precalculated box (X25519 + XSalsa20-Poly1305)
    final decrypted = _precalculatedBox!.openEasy(
      cipherText: ciphertext,
      nonce: nonce,
    );
    
    return json.decode(utf8.decode(decrypted));
  }
  
  /// Check if encryption session is active
  bool get isSessionActive => _sessionEstablished && _precalculatedBox != null;
  
  /// Get client ID for this session
  String? get clientId => _clientId;
  
  /// Reset session (for new handshake)
  void resetSession() {
    _sessionPrivateKey?.dispose();
    _sessionPrivateKey = null;
    _sessionPublicKey = null;
    _serverPublicKey = null;
    _sharedSecret?.dispose();
    _sharedSecret = null;
    _precalculatedBox = null;
    _sessionEstablished = false;
  }
  
  /// Clear all keys and reset service
  Future<void> clearAllKeys() async {
    await _secureStorage.delete(key: _identityKeyKey);
    await _secureStorage.delete(key: _identityPublicKeyKey);
    resetSession();
    _identityPrivateKey?.dispose();
    _identityPrivateKey = null;
    _identityPublicKey = null;
    _clientId = null;
  }
  
  // Utility methods
  
  String _bytesToHex(Uint8List bytes) {
    return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  }
  
  Uint8List _hexToBytes(String hex) {
    final result = Uint8List(hex.length ~/ 2);
    for (int i = 0; i < hex.length; i += 2) {
      result[i ~/ 2] = int.parse(hex.substring(i, i + 2), radix: 16);
    }
    return result;
  }
  
  /// Dispose of all secure keys
  void dispose() {
    _identityPrivateKey?.dispose();
    _sessionPrivateKey?.dispose();
    _sharedSecret?.dispose();
  }
}

/// Exception thrown when encryption operations fail
class EncryptionException implements Exception {
  final String message;
  const EncryptionException(this.message);
  
  @override
  String toString() => 'EncryptionException: $message';
}
