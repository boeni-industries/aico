import 'dart:convert';
import 'dart:io';

import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

/// Unified API client that handles both encrypted and unencrypted requests
/// Uses Dio for primary requests with http as fallback
class UnifiedApiClient {
  final EncryptionService _encryptionService;
  final TokenManager _tokenManager;
  
  Dio? _dio;
  http.Client? _httpClient;
  
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
    if (_isInitialized) return;
    
    // Initialize encryption service first
    await _encryptionService.initialize();
    
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
    _dio!.interceptors.add(LogInterceptor(
      requestBody: kDebugMode,
      responseBody: kDebugMode,
      logPrint: (obj) => debugPrint(obj.toString()),
    ));

    // Initialize HTTP client
    _httpClient = http.Client();
    
    _isInitialized = true;
    debugPrint('UnifiedApiClient initialized with base URL: $_baseUrl');
    AICOLog.info('UnifiedApiClient initialized', 
      topic: 'network/client/init', 
      extra: {'base_url': _baseUrl});
  }

  /// Make a request with automatic encryption detection
  Future<T?> request<T>(
    String method,
    String endpoint, {
    Map<String, dynamic>? data,
    Map<String, String>? queryParameters,
    T Function(Map<String, dynamic>)? fromJson,
    bool skipTokenRefresh = false,
  }) async {
    // Auto-initialize if not done yet
    if (!_isInitialized) {
      await initialize();
    }

    final needsEncryption = _requiresEncryption(endpoint);
    
    try {
      if (needsEncryption) {
        return await _makeEncryptedRequest<T>(
          method,
          endpoint,
          data: data,
          queryParameters: queryParameters,
          fromJson: fromJson,
          skipTokenRefresh: skipTokenRefresh,
        );
      } else {
        return await _makeUnencryptedRequest<T>(
          method,
          endpoint,
          data: data,
          queryParameters: queryParameters,
          fromJson: fromJson,
          skipTokenRefresh: skipTokenRefresh,
        );
      }
    } catch (e) {
      debugPrint('UnifiedApiClient request failed: $e');
      AICOLog.error('API request failed', 
        topic: 'network/client/request/error',
        extra: {'method': method, 'endpoint': endpoint, 'error': e.toString()});
      rethrow;
    }
  }


  /// Make encrypted request using EncryptionService
  Future<T?> _makeEncryptedRequest<T>(
    String method,
    String endpoint, {
    Map<String, dynamic>? data,
    Map<String, String>? queryParameters,
    T Function(Map<String, dynamic>)? fromJson,
    bool skipTokenRefresh = false,
  }) async {
    // Ensure encryption session is active
    if (!_encryptionService.isSessionActive) {
      AICOLog.info('Starting encryption handshake', 
        topic: 'network/encryption/handshake/start',
        extra: {'endpoint': endpoint});
      await _performHandshake();
    }

    // Prepare headers (including Authorization for authenticated endpoints)
    final headers = await _buildHeaders(skipTokenRefresh: skipTokenRefresh);
    
    // Create encrypted request payload
    Map<String, dynamic> requestData;
    if (data != null) {
      // Use EncryptionService to create properly encrypted request
      requestData = _encryptionService.createEncryptedRequest(data);
    } else {
      // Even for requests without data, we need to encrypt an empty payload
      requestData = _encryptionService.createEncryptedRequest({});
    }

    // Make request with Dio to the same HTTP endpoint but with encrypted payload
    final response = await _dio!.request(
      endpoint,
      data: requestData,
      queryParameters: queryParameters,
      options: Options(
        method: method,
        headers: headers,
      ),
    );

    // Process and decrypt response if needed
    if (response.data != null && response.data is Map<String, dynamic>) {
      final responseMap = response.data;
      
      // Check if response is encrypted
      if (responseMap.containsKey('encrypted') && 
          responseMap['encrypted'] == true && 
          responseMap.containsKey('payload')) {
        // Decrypt the response payload
        final decryptedData = _encryptionService.decryptPayload(responseMap['payload']);
        return _processResponse<T>(decryptedData, fromJson);
      }
    }

    return _processResponse<T>(response.data, fromJson);
  }

  /// Make unencrypted request using Dio with HTTP fallback
  Future<T?> _makeUnencryptedRequest<T>(
    String method,
    String endpoint, {
    Map<String, dynamic>? data,
    Map<String, String>? queryParameters,
    T Function(Map<String, dynamic>)? fromJson,
    bool skipTokenRefresh = false,
  }) async {
    try {
      // Try Dio first
      final headers = await _buildHeaders(skipTokenRefresh: skipTokenRefresh);
      
      final response = await _dio!.request(
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
      AICOLog.warn('Dio request failed, using HTTP fallback', 
        topic: 'network/client/fallback',
        extra: {'method': method, 'endpoint': endpoint, 'error': e.toString()});
      
      // Fallback to HTTP client
      return await _makeHttpRequest<T>(
        method,
        endpoint,
        data: data,
        queryParameters: queryParameters,
        fromJson: fromJson,
        skipTokenRefresh: skipTokenRefresh,
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
    bool skipTokenRefresh = false,
  }) async {
    final uri = Uri.parse('$_baseUrl$endpoint').replace(
      queryParameters: queryParameters,
    );

    final headers = await _buildHeaders(skipTokenRefresh: skipTokenRefresh);
    
    http.Response response;
    
    switch (method.toUpperCase()) {
      case 'GET':
        response = await _httpClient!.get(uri, headers: headers);
        break;
      case 'POST':
        response = await _httpClient!.post(
          uri,
          headers: headers,
          body: data != null ? json.encode(data) : null,
        );
        break;
      case 'PUT':
        response = await _httpClient!.put(
          uri,
          headers: headers,
          body: data != null ? json.encode(data) : null,
        );
        break;
      case 'DELETE':
        response = await _httpClient!.delete(uri, headers: headers);
        break;
      default:
        throw ArgumentError('Unsupported HTTP method: $method');
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      final responseData = json.decode(response.body);
      AICOLog.debug('HTTP request successful', 
        topic: 'network/http/success',
        extra: {'method': method, 'endpoint': endpoint, 'status_code': response.statusCode});
      return _processResponse<T>(responseData, fromJson);
    } else {
      AICOLog.error('HTTP request failed', 
        topic: 'network/http/error',
        extra: {'method': method, 'endpoint': endpoint, 'status_code': response.statusCode, 'response_body': response.body});
      throw HttpException('HTTP ${response.statusCode}: ${response.body}');
    }
  }

  /// Convenience method for GET requests
  Future<T?> get<T>(
    String endpoint, {
    Map<String, String>? queryParameters,
    T Function(Map<String, dynamic>)? fromJson,
  }) async {
    return request<T>(
      'GET',
      endpoint,
      queryParameters: queryParameters,
      fromJson: fromJson,
    );
  }

  /// Convenience method for POST requests
  Future<Map<String, dynamic>?> post(
    String endpoint, {
    Map<String, dynamic>? data,
    Map<String, String>? queryParameters,
  }) async {
    return await request<Map<String, dynamic>>(
      'POST',
      endpoint,
      data: data,
      queryParameters: queryParameters,
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  /// Make a POST request for token refresh (skips token freshness check)
  Future<Map<String, dynamic>?> postForTokenRefresh(
    String endpoint, {
    Map<String, dynamic>? data,
    Map<String, String>? queryParameters,
  }) async {
    // Auto-initialize if not done yet
    if (!_isInitialized) {
      await initialize();
    }

    // Ensure encryption session is active for token refresh
    if (!_encryptionService.isSessionActive) {
      debugPrint('🔐 UnifiedApiClient: Starting encryption handshake for token refresh');
      await _performHandshake();
    }

    // Use encrypted request directly with skip token refresh flag
    return await _makeEncryptedRequest<Map<String, dynamic>>(
      'POST',
      endpoint,
      data: data,
      queryParameters: queryParameters,
      fromJson: (json) => json as Map<String, dynamic>,
      skipTokenRefresh: true,
    );
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
      data = responseData;
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
    
    final response = await _dio!.post(
      '/handshake',
      data: handshakeRequest,
    );

    await _encryptionService.processHandshakeResponse(response.data);
  }

  /// Build headers for HTTP requests
  Future<Map<String, String>> _buildHeaders({bool skipTokenRefresh = false}) async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'User-Agent': 'AICO-Flutter/1.0',
    };

    // Skip token refresh for refresh requests to avoid circular dependency
    if (!skipTokenRefresh) {
      await _tokenManager.ensureTokenFreshness();
    }

    // Add authentication token if available
    final token = await _tokenManager.getAccessToken();
    debugPrint('UnifiedApiClient: Token retrieved: ${token != null ? "YES (${token.substring(0, 20)}...)" : "NO"}');
    AICOLog.info('Building headers for request', 
      topic: 'network/client/headers',
      extra: {'has_token': token != null, 'token_preview': token?.substring(0, 20)});
    
    if (token != null) {
      headers['Authorization'] = 'Bearer $token';
      debugPrint('UnifiedApiClient: Authorization header added');
    } else {
      debugPrint('UnifiedApiClient: No token available, Authorization header NOT added');
    }

    return headers;
  }

  /// Determine if endpoint requires encryption
  bool _requiresEncryption(String endpoint) {
    // Public endpoints that don't require encryption (must match backend middleware)
    const publicEndpoints = [
      '/health',
      '/handshake',
    ];

    return !publicEndpoints.any((public) => endpoint.startsWith(public));
  }

  /// Dispose of resources
  Future<void> dispose() async {
    _dio?.close();
    _httpClient?.close();
  }
}
