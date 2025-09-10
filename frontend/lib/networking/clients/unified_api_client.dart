import 'dart:convert';
import 'dart:io';

import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

/// Unified API client that handles both encrypted and unencrypted requests
/// Uses Dio for primary requests with http as fallback
class UnifiedApiClient {
  final EncryptionService _encryptionService;
  final TokenManager _tokenManager;
  
  late final Dio _dio;
  late final http.Client _httpClient;
  
  String _baseUrl = 'http://localhost:8771/api/v1';
  bool _isInitialized = false;

  UnifiedApiClient({
    required EncryptionService encryptionService,
    required TokenManager tokenManager,
    String? baseUrl,
  }) : _encryptionService = encryptionService,
       _tokenManager = tokenManager {
    if (baseUrl != null) {
      _baseUrl = baseUrl;
    }
  }

  /// Initialize the client with proper configuration
  Future<void> initialize() async {
    // Initialize Dio
    _dio = Dio(BaseOptions(
      baseUrl: _baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      sendTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ));

    // Add interceptors
    _dio.interceptors.add(LogInterceptor(
      requestBody: kDebugMode,
      responseBody: kDebugMode,
      logPrint: (obj) => debugPrint(obj.toString()),
    ));

    // Initialize HTTP client
    _httpClient = http.Client();
    
    _isInitialized = true;
  }

  /// Make a request with automatic encryption detection
  Future<T?> request<T>(
    String method,
    String endpoint, {
    Map<String, dynamic>? data,
    Map<String, String>? queryParameters,
    T Function(Map<String, dynamic>)? fromJson,
  }) async {
    if (!_isInitialized) {
      throw StateError('UnifiedApiClient not initialized. Call initialize() first.');
    }

    final needsEncryption = _requiresEncryption(endpoint);
    
    try {
      if (needsEncryption && _encryptionService.isInitialized) {
        return await _makeEncryptedRequest<T>(
          method,
          endpoint,
          data: data,
          queryParameters: queryParameters,
          fromJson: fromJson,
        );
      } else {
        return await _makeUnencryptedRequest<T>(
          method,
          endpoint,
          data: data,
          queryParameters: queryParameters,
          fromJson: fromJson,
        );
      }
    } catch (e) {
      debugPrint('UnifiedApiClient request failed: $e');
      rethrow;
    }
  }

  /// Make encrypted request using Dio
  Future<T?> _makeEncryptedRequest<T>(
    String method,
    String endpoint, {
    Map<String, dynamic>? data,
    Map<String, String>? queryParameters,
    T Function(Map<String, dynamic>)? fromJson,
  }) async {
    // Ensure encryption session is active
    if (!_encryptionService.isSessionActive) {
      await _performHandshake();
    }

    // Prepare headers
    final headers = await _buildHeaders();
    
    // Encrypt payload if present
    Map<String, dynamic>? requestData;
    if (data != null) {
      requestData = _encryptionService.createEncryptedRequest(data);
    }

    // Make request with Dio
    final response = await _dio.request(
      endpoint,
      data: requestData,
      queryParameters: queryParameters,
      options: Options(
        method: method,
        headers: headers,
      ),
    );

    return _processResponse<T>(response.data, fromJson);
  }

  /// Make unencrypted request using Dio with HTTP fallback
  Future<T?> _makeUnencryptedRequest<T>(
    String method,
    String endpoint, {
    Map<String, dynamic>? data,
    Map<String, String>? queryParameters,
    T Function(Map<String, dynamic>)? fromJson,
  }) async {
    try {
      // Try Dio first
      final headers = await _buildHeaders();
      
      final response = await _dio.request(
        endpoint,
        data: data,
        queryParameters: queryParameters,
        options: Options(
          method: method,
          headers: headers,
        ),
      );

      return _processResponse<T>(response.data, fromJson);
    } catch (e) {
      debugPrint('Dio request failed, falling back to HTTP: $e');
      
      // Fallback to HTTP client
      return await _makeHttpRequest<T>(
        method,
        endpoint,
        data: data,
        queryParameters: queryParameters,
        fromJson: fromJson,
      );
    }
  }

  /// Fallback HTTP request
  Future<T?> _makeHttpRequest<T>(
    String method,
    String endpoint, {
    Map<String, dynamic>? data,
    Map<String, String>? queryParameters,
    T Function(Map<String, dynamic>)? fromJson,
  }) async {
    final uri = Uri.parse('$_baseUrl$endpoint').replace(
      queryParameters: queryParameters,
    );

    final headers = await _buildHeaders();
    
    http.Response response;
    
    switch (method.toUpperCase()) {
      case 'GET':
        response = await _httpClient.get(uri, headers: headers);
        break;
      case 'POST':
        response = await _httpClient.post(
          uri,
          headers: headers,
          body: data != null ? json.encode(data) : null,
        );
        break;
      case 'PUT':
        response = await _httpClient.put(
          uri,
          headers: headers,
          body: data != null ? json.encode(data) : null,
        );
        break;
      case 'DELETE':
        response = await _httpClient.delete(uri, headers: headers);
        break;
      default:
        throw ArgumentError('Unsupported HTTP method: $method');
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      final responseData = json.decode(response.body);
      return _processResponse<T>(responseData, fromJson);
    } else {
      throw HttpException('HTTP ${response.statusCode}: ${response.body}');
    }
  }

  /// Process response and handle decryption if needed
  T? _processResponse<T>(
    dynamic responseData,
    T Function(Map<String, dynamic>)? fromJson,
  ) {
    if (responseData == null) return null;

    Map<String, dynamic> data;
    
    // Handle encrypted responses
    if (responseData is Map<String, dynamic> && 
        responseData.containsKey('encrypted') && 
        responseData['encrypted'] == true) {
      data = _encryptionService.decryptPayload(responseData['payload']);
    } else {
      data = responseData as Map<String, dynamic>;
    }

    // Apply JSON transformation if provided
    if (fromJson != null) {
      return fromJson(data);
    }

    return data as T?;
  }

  /// Perform encryption handshake with backend
  Future<void> _performHandshake() async {
    final handshakeRequest = await _encryptionService.createHandshakeRequest();
    
    final response = await _dio.post(
      '/auth/handshake',
      data: handshakeRequest,
    );

    await _encryptionService.processHandshakeResponse(response.data);
  }

  /// Build request headers with authentication
  Future<Map<String, String>> _buildHeaders() async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    // Add authentication token if available
    final token = await _tokenManager.getAccessToken();
    if (token != null) {
      headers['Authorization'] = 'Bearer $token';
    }

    return headers;
  }

  /// Determine if endpoint requires encryption
  bool _requiresEncryption(String endpoint) {
    // Public endpoints that don't require encryption
    const publicEndpoints = [
      '/health',
      '/auth/login',
      '/auth/register',
      '/auth/handshake',
    ];

    return !publicEndpoints.any((public) => endpoint.startsWith(public));
  }

  /// Dispose of resources
  Future<void> dispose() async {
    _dio.close();
    _httpClient.close();
  }
}
