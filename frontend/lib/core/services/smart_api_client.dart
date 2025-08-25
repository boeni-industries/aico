import 'package:aico_frontend/core/services/encrypted_api_client.dart';
import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/networking/clients/api_client.dart';
import 'package:dio/dio.dart';

/// Smart API client that automatically determines when to use encryption
/// based on endpoint patterns, eliminating the need for manual routing
class SmartApiClient {
  final AicoApiClient _plainClient;
  final EncryptedApiService _encryptedClient;
  
  // Endpoints that should NOT be encrypted (from backend middleware)
  static const _unencryptedPaths = [
    '/health',
    '/gateway/status', 
    '/gateway/metrics',
    '/docs',
    '/redoc',
    '/openapi.json',
    '/handshake', // Special case - handled by middleware
  ];

  SmartApiClient(Dio dio) 
    : _plainClient = AicoApiClient(dio),
      _encryptedClient = EncryptedApiService(
          EncryptedApiClient(dio), 
          EncryptionService()
        );

  /// Initialize encryption session (call once at app start)
  Future<void> initializeEncryption() async {
    await _encryptedClient.establishEncryptedSession();
  }

  /// Smart request that auto-detects encryption requirement
  Future<T> request<T>(
    String method,
    String endpoint,
    {
    Map<String, dynamic>? data,
    Map<String, dynamic>? queryParameters,
    T Function(Map<String, dynamic>)? fromJson,
  }) async {
    
    // Check if endpoint requires encryption
    final needsEncryption = _requiresEncryption(endpoint);
    
    if (needsEncryption) {
      // Use encrypted client
      final response = await _encryptedClient.sendEncryptedRequest(
        method, 
        endpoint, 
        data ?? {}
      );
      
      if (fromJson != null) {
        return fromJson(response);
      }
      return response as T;
      
    } else {
      // Use plain client with Dio directly
      final dio = Dio(BaseOptions(baseUrl: 'http://localhost:8771/api/v1'));
      final response = await dio.request(
        endpoint,
        data: data,
        queryParameters: queryParameters,
        options: Options(method: method),
      );
      
      if (fromJson != null) {
        return fromJson(response.data);
      }
      return response.data as T;
    }
  }

  /// Determine if endpoint requires encryption based on path patterns
  bool _requiresEncryption(String endpoint) {
    // Remove leading slash for consistent comparison
    final path = endpoint.startsWith('/') ? endpoint.substring(1) : endpoint;
    
    // Check against unencrypted paths
    for (final unencryptedPath in _unencryptedPaths) {
      final cleanUnencryptedPath = unencryptedPath.startsWith('/') 
        ? unencryptedPath.substring(1) 
        : unencryptedPath;
        
      if (path.startsWith(cleanUnencryptedPath)) {
        return false;
      }
    }
    
    // Default: require encryption for all other endpoints
    return true;
  }

  /// Convenience methods for common HTTP verbs
  Future<T> get<T>(String endpoint, {T Function(Map<String, dynamic>)? fromJson}) =>
    request<T>('GET', endpoint, fromJson: fromJson);

  Future<T> post<T>(String endpoint, Map<String, dynamic> data, {T Function(Map<String, dynamic>)? fromJson}) =>
    request<T>('POST', endpoint, data: data, fromJson: fromJson);

  Future<T> put<T>(String endpoint, Map<String, dynamic> data, {T Function(Map<String, dynamic>)? fromJson}) =>
    request<T>('PUT', endpoint, data: data, fromJson: fromJson);

  Future<T> delete<T>(String endpoint, {T Function(Map<String, dynamic>)? fromJson}) =>
    request<T>('DELETE', endpoint, fromJson: fromJson);

  /// Access to underlying clients if needed
  AicoApiClient get plainClient => _plainClient;
  EncryptedApiService get encryptedClient => _encryptedClient;
  
  /// Check encryption status
  bool get isEncryptionActive => _encryptedClient.isEncryptionActive;
  String get encryptionStatus => _encryptedClient.encryptionStatus;
}
