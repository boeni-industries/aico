import 'dart:convert';

import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/networking/models/handshake_models.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
/// Unified API client that transparently routes requests to encrypted or plain endpoints.
/// Handles handshake, encryption, error handling, and smart endpoint detection.
class UnifiedApiClient {
  final Dio _dio;
  final http.Client _httpClient;
  final EncryptionService _encryptionService;
  final String _baseUrl;
  final Map<String, String> _defaultHeaders;

  // Endpoints that should NOT be encrypted
  static const _unencryptedPaths = [
    '/health',
    '/gateway/status',
    '/gateway/metrics',
    '/docs',
    '/redoc',
    '/openapi.json',
    '/handshake',
  ];

  bool _handshakeCompleted = false;
  String? _encryptionStatus;

  UnifiedApiClient({
    required Dio dio,
    required http.Client httpClient,
    required EncryptionService encryptionService,
    required String baseUrl,
    Map<String, String>? defaultHeaders,
  })  : _dio = dio,
        _httpClient = httpClient,
        _encryptionService = encryptionService,
        _baseUrl = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl,
        _defaultHeaders = {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...?defaultHeaders,
        };

  /// Initialize handshake for encrypted endpoints
  Future<void> initializeEncryption() async {
    try {
      debugPrint('🔐 UnifiedApiClient: Starting encryption initialization...');
      _encryptionStatus = 'Establishing handshake...';
      
      debugPrint('🔐 UnifiedApiClient: Creating handshake request...');
      final handshakeData = await _encryptionService.createHandshakeRequest();
      final request = HandshakeRequest(handshakeRequest: handshakeData['handshake_request']);
      
      final handshakeUrl = '$_baseUrl/handshake';
      debugPrint('🔐 UnifiedApiClient: _baseUrl = $_baseUrl');
      debugPrint('🔐 UnifiedApiClient: Full handshake URL = $handshakeUrl');
      debugPrint('🔐 UnifiedApiClient: Sending handshake request...');
      final response = await _dio.post(handshakeUrl, data: request.toJson());
      debugPrint('🔐 UnifiedApiClient: Handshake response received: ${response.statusCode}');
      
      debugPrint('🔐 UnifiedApiClient: Processing handshake response...');
      await _encryptionService.processHandshakeResponse(response.data);
      
      _handshakeCompleted = true;
      _encryptionStatus = 'Encrypted (Active)';
      debugPrint('✅ UnifiedApiClient: Encryption session established successfully');
    } catch (e) {
      _handshakeCompleted = false;
      _encryptionStatus = 'Encryption Failed: ${e.toString()}';
      debugPrint('❌ UnifiedApiClient: Encryption initialization failed: $e');
      debugPrint('❌ UnifiedApiClient: Error type: ${e.runtimeType}');
      throw EncryptionConnectionException('Failed to establish encrypted session: $e');
    }
  }

  /// Smart request that auto-detects encryption requirement
  Future<T> request<T>(
    String method,
    String endpoint, {
    Map<String, dynamic>? data,
    Map<String, dynamic>? queryParameters,
    T Function(Map<String, dynamic>)? fromJson,
    Map<String, String>? headers,
  }) async {
    final needsEncryption = _requiresEncryption(endpoint);
    if (needsEncryption) {
      if (!_handshakeCompleted || !_encryptionService.isSessionActive) {
        throw EncryptionConnectionException('No active encryption session. Call initializeEncryption() first.');
      }
      // Encrypt payload
      final encryptedPayload = data != null ? _encryptionService.encryptPayload(data) : null;
      final encryptedRequest = {
        'encrypted': true,
        'payload': encryptedPayload,
        'client_id': _encryptionService.clientId, // Match backend expectation
      };
      try {
        final response = await _dio.request(
          endpoint,
          data: encryptedRequest,
          options: Options(method: method, headers: {'Content-Type': 'application/json', ...?headers}),
        );
        // Decrypt response if needed
        final responseData = response.data;
        if (responseData is Map<String, dynamic> && responseData['encrypted'] == true && responseData.containsKey('encrypted_payload')) {
          final decrypted = _encryptionService.decryptPayload(responseData['encrypted_payload']);
          if (fromJson != null) return fromJson(decrypted);
          return decrypted as T;
        } else {
          if (fromJson != null) return fromJson(responseData);
          return responseData as T;
        }
      } catch (e) {
        _encryptionStatus = 'Encryption Error: ${e.toString()}';
        throw EncryptionConnectionException('Encrypted request failed: $e');
      }
    } else {
      // Plain HTTP request
      try {
        final uri = _buildUri(endpoint, queryParameters);
        late http.Response response;
        switch (method.toUpperCase()) {
          case 'GET':
            response = await _httpClient.get(uri, headers: {..._defaultHeaders, ...?headers});
            break;
          case 'POST':
            response = await _httpClient.post(uri, headers: {..._defaultHeaders, ...?headers}, body: data != null ? jsonEncode(data) : null);
            break;
          case 'PUT':
            response = await _httpClient.put(uri, headers: {..._defaultHeaders, ...?headers}, body: data != null ? jsonEncode(data) : null);
            break;
          case 'DELETE':
            response = await _httpClient.delete(uri, headers: {..._defaultHeaders, ...?headers});
            break;
          default:
            throw ApiException('Unsupported HTTP method: $method');
        }
        return _handleHttpResponse<T>(response, fromJson);
      } catch (e) {
        throw ApiException('$method $endpoint failed: $e');
      }
    }
  }

  // Convenience methods
  Future<T> get<T>(String endpoint, {Map<String, dynamic>? queryParameters, T Function(Map<String, dynamic>)? fromJson, Map<String, String>? headers}) =>
      request<T>('GET', endpoint, queryParameters: queryParameters, fromJson: fromJson, headers: headers);
  Future<T> post<T>(String endpoint, Map<String, dynamic> data, {T Function(Map<String, dynamic>)? fromJson, Map<String, String>? headers}) =>
      request<T>('POST', endpoint, data: data, fromJson: fromJson, headers: headers);
  Future<T> put<T>(String endpoint, Map<String, dynamic> data, {T Function(Map<String, dynamic>)? fromJson, Map<String, String>? headers}) =>
      request<T>('PUT', endpoint, data: data, fromJson: fromJson, headers: headers);
  Future<T> delete<T>(String endpoint, {T Function(Map<String, dynamic>)? fromJson, Map<String, String>? headers}) =>
      request<T>('DELETE', endpoint, fromJson: fromJson, headers: headers);

  /// Build URI with query parameters for http package
  Uri _buildUri(String endpoint, [Map<String, dynamic>? queryParams]) {
    final url = '$_baseUrl$endpoint';
    if (queryParams != null && queryParams.isNotEmpty) {
      return Uri.parse(url).replace(queryParameters: queryParams.map((k, v) => MapEntry(k, v.toString())));
    }
    return Uri.parse(url);
  }

  /// Handle HTTP response with unified error handling
  T _handleHttpResponse<T>(http.Response response, T Function(Map<String, dynamic>)? fromJson) {
    final statusCode = response.statusCode;
    Map<String, dynamic>? responseData;
    try {
      if (response.body.isNotEmpty) {
        responseData = jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      throw ApiException('Failed to parse response JSON: $e');
    }
    if (statusCode >= 200 && statusCode < 300) {
      if (fromJson != null && responseData != null) {
        try {
          return fromJson(responseData);
        } catch (e) {
          throw ApiException('Failed to deserialize response: $e');
        }
      }
      return responseData as T;
    } else {
      final errorMessage = responseData?['message'] ?? responseData?['error'] ?? 'HTTP $statusCode';
      throw ApiException(errorMessage, statusCode: statusCode, responseData: responseData);
    }
  }

  // Encryption status for UI
  String get encryptionStatus => _encryptionStatus ?? 'Not initialized';
  bool get isEncryptionActive => _handshakeCompleted && _encryptionService.isSessionActive;

  void resetEncryption() {
    _encryptionService.resetSession();
    _handshakeCompleted = false;
    _encryptionStatus = 'Reset - Not encrypted';
  }

  void dispose() {
    _httpClient.close();
  }

  bool _requiresEncryption(String endpoint) {
    final path = endpoint.startsWith('/') ? endpoint.substring(1) : endpoint;
    for (final unencryptedPath in _unencryptedPaths) {
      final cleanUnencryptedPath = unencryptedPath.startsWith('/') ? unencryptedPath.substring(1) : unencryptedPath;
      if (path.startsWith(cleanUnencryptedPath)) {
        return false;
      }
    }
    return true;
  }
}

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final Map<String, dynamic>? responseData;
  const ApiException(this.message, {this.statusCode, this.responseData});
  @override
  String toString() {
    if (statusCode != null) {
      return 'ApiException($statusCode): $message';
    }
    return 'ApiException: $message';
  }
  bool get isNetworkError => statusCode == null;
  bool get isClientError => statusCode != null && statusCode! >= 400 && statusCode! < 500;
  bool get isServerError => statusCode != null && statusCode! >= 500;
}

class EncryptionConnectionException implements Exception {
  final String message;
  const EncryptionConnectionException(this.message);
  @override
  String toString() => 'EncryptionConnectionException: $message';
}
