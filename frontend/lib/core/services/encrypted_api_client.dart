import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/networking/models/handshake_models.dart';
import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

part 'encrypted_api_client.g.dart';

/// Encrypted API client with handshake and echo endpoints
/// SECURITY: Never falls back to plain HTTP - encryption failures are treated as connection errors
@RestApi(baseUrl: "http://localhost:8771/api/v1")
abstract class EncryptedApiClient {
  factory EncryptedApiClient(Dio dio, {String baseUrl}) = _EncryptedApiClient;

  // Handshake endpoint for establishing encryption session
  @POST("/handshake")
  Future<HandshakeResponse> performHandshake(@Body() HandshakeRequest request);

  // Echo endpoint for testing encrypted communication
  @POST("/echo")
  Future<EncryptedResponse> echoEncrypted(@Body() EncryptedRequest request);
}

/// Wrapper service that manages encrypted communication
class EncryptedApiService {
  final EncryptedApiClient _client;
  final EncryptionService _encryptionService;
  
  bool _handshakeCompleted = false;
  String? _encryptionStatus;

  EncryptedApiService(this._client, this._encryptionService);

  /// Get current encryption status for UI display
  String get encryptionStatus => _encryptionStatus ?? 'Not initialized';
  
  /// Check if encryption is active
  bool get isEncryptionActive => _handshakeCompleted && _encryptionService.isSessionActive;

  /// Perform handshake to establish encrypted session
  /// CRITICAL: This must succeed before any encrypted communication
  Future<void> establishEncryptedSession() async {
    try {
      _encryptionStatus = 'Establishing handshake...';
      
      // Create handshake request
      final handshakeData = await _encryptionService.createHandshakeRequest();
      final request = HandshakeRequest(handshakeRequest: handshakeData['handshake_request']);
      
      // Send handshake to backend
      final response = await _client.performHandshake(request);
      
      // Process handshake response
      await _encryptionService.processHandshakeResponse(response.toJson());
      
      _handshakeCompleted = true;
      _encryptionStatus = 'Encrypted (Active)';
      
    } catch (e) {
      _handshakeCompleted = false;
      _encryptionStatus = 'Encryption Failed: ${e.toString()}';
      
      // SECURITY: Do not fall back to plain HTTP - throw error
      throw EncryptionConnectionException(
        'Failed to establish encrypted session: $e'
      );
    }
  }

  /// Test encrypted communication with echo endpoint
  Future<EchoResponse> testEncryptedEcho(String message) async {
    if (!isEncryptionActive) {
      throw EncryptionConnectionException(
        'No active encryption session - call establishEncryptedSession() first'
      );
    }

    try {
      // Create echo request
      final echoRequest = EchoRequest(
        message: message,
        timestamp: DateTime.now().millisecondsSinceEpoch,
      );

      // Encrypt the request
      final encryptedPayload = _encryptionService.encryptPayload(echoRequest.toJson());
      final encryptedRequest = EncryptedRequest(
        encrypted: true,
        payload: encryptedPayload,
        clientId: _encryptionService.clientId!,
      );

      // Send encrypted request
      final response = await _client.echoEncrypted(encryptedRequest);

      // Decrypt response
      final decryptedPayload = _encryptionService.decryptPayload(response.payload);
      return EchoResponse.fromJson(decryptedPayload);

    } catch (e) {
      _encryptionStatus = 'Encryption Error: ${e.toString()}';
      throw EncryptionConnectionException('Encrypted communication failed: $e');
    }
  }


  /// Send encrypted request to any endpoint
  Future<Map<String, dynamic>> sendEncryptedRequest(
    String method,
    String endpoint,
    Map<String, dynamic> payload,
  ) async {
    if (!isEncryptionActive) {
      throw EncryptionConnectionException(
        'No active encryption session - establish encryption first'
      );
    }

    try {
      // Encrypt the payload
      final encryptedPayload = _encryptionService.encryptPayload(payload);
      final encryptedRequest = EncryptedRequest(
        encrypted: true,
        payload: encryptedPayload,
        clientId: _encryptionService.clientId!,
      );

      // Send encrypted request using Dio directly
      final dio = Dio(BaseOptions(baseUrl: 'http://localhost:8771/api/v1'));
      final response = await dio.request(
        endpoint,
        data: encryptedRequest.toJson(),
        options: Options(
          method: method,
          headers: {'Content-Type': 'application/json'},
        ),
      );

      // Check if response is encrypted
      if (response.data is Map<String, dynamic>) {
        final responseData = response.data as Map<String, dynamic>;
        if (responseData['encrypted'] == true && responseData.containsKey('encrypted_payload')) {
          // Decrypt response
          final decryptedPayload = _encryptionService.decryptPayload(responseData['encrypted_payload']);
          return decryptedPayload;
        }
      }

      // Return unencrypted response (shouldn't happen for encrypted endpoints)
      return response.data;

    } catch (e) {
      _encryptionStatus = 'Encryption Error: ${e.toString()}';
      throw EncryptionConnectionException('Encrypted request failed: $e');
    }
  }

  /// Reset encryption session
  void resetEncryption() {
    _encryptionService.resetSession();
    _handshakeCompleted = false;
    _encryptionStatus = 'Reset - Not encrypted';
  }

  /// Get encrypted API client for handshake and echo operations
  EncryptedApiClient get encryptedClient => _client;
}

/// Exception for encryption-related connection failures
/// SECURITY: These should never be silently handled - user must be informed
class EncryptionConnectionException implements Exception {
  final String message;
  const EncryptionConnectionException(this.message);
  
  @override
  String toString() => 'EncryptionConnectionException: $message';
}
