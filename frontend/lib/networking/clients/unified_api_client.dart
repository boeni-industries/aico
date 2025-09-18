import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../../core/logging/aico_log.dart';
import '../../core/services/encryption_service.dart';
import '../exceptions/api_exceptions.dart';
import '../services/connection_manager.dart';
import '../services/token_manager.dart';

/// Unified API client that handles both encrypted and unencrypted requests
/// Uses Dio exclusively for all HTTP operations
class UnifiedApiClient {
  final EncryptionService _encryptionService;
  final TokenManager _tokenManager;
  final ConnectionManager _connectionManager;
  
  Dio? _dio;
  String? _baseUrl;
  
  static const Duration _defaultTimeout = Duration(seconds: 120);
  static const String _defaultBaseUrl = 'http://localhost:8771/api/v1';
  bool _isInitialized = false;

  UnifiedApiClient({
    required EncryptionService encryptionService,
    required TokenManager tokenManager,
    required ConnectionManager connectionManager,
  }) : _encryptionService = encryptionService,
       _tokenManager = tokenManager,
       _connectionManager = connectionManager {
    _tokenManager.setApiClient(this);
  }

  /// Initialize the client with proper configuration
  Future<void> initialize() async {
    if (_isInitialized) return;
    
    try {
      // Initialize encryption service first
      await _encryptionService.initialize();
      
      // Initialize Dio
      _dio = Dio(BaseOptions(
        baseUrl: _baseUrl ?? _defaultBaseUrl,
        connectTimeout: _defaultTimeout,
        receiveTimeout: _defaultTimeout,
        sendTimeout: _defaultTimeout,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        // Configure validateStatus to not throw exceptions for expected error codes
        validateStatus: (status) {
          // Don't throw exceptions for any status code - we'll handle them manually
          return status != null && status < 500; // Only throw for server errors (500+)
        },
      ));

      // Add minimal logging interceptor for errors only
      _dio!.interceptors.add(LogInterceptor(
        requestBody: false,
        responseBody: false,
        requestHeader: false,
        responseHeader: false,
        request: false,
        error: true,
        logPrint: (obj) => AICOLog.debug(obj.toString(), topic: 'network/dio/error'),
      ));

      _isInitialized = true;
      AICOLog.info('UnifiedApiClient initialized', 
        topic: 'network/client/init', 
        extra: {'base_url': _baseUrl});
    } catch (e) {
      // Handle initialization errors gracefully - don't let them crash the app
      AICOLog.warn('UnifiedApiClient initialization failed, will retry on first request', 
        topic: 'network/client/init_error', 
        extra: {'error': e.toString()});
      // Don't set _isInitialized to true, so it will retry on first request
    }
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

    // All requests are encrypted - backend only supports encrypted connections
    try {
      return await _makeEncryptedRequest<T>(
        method,
        endpoint,
        data: data,
        fromJson: fromJson,
        skipTokenRefresh: skipTokenRefresh,
      );
    } catch (e) {
      AICOLog.error('API request failed', 
        topic: 'network/client/request/error',
        extra: {'method': method, 'endpoint': endpoint, 'error': e.toString()});
      rethrow;
    }
  }

  /// Make encrypted request with proper error handling and retry logic
  Future<T?> _makeEncryptedRequest<T>(
    String method,
    String endpoint, {
    Map<String, dynamic>? data,
    T Function(Map<String, dynamic>)? fromJson,
    bool skipTokenRefresh = false,
  }) async {
    if (!_isInitialized) {
      await initialize();
    }

    // Check if device is offline
    if (!_connectionManager.isOnline) {
      debugPrint('📱 [UnifiedApiClient] Device offline - returning null');
      return null; // Return null instead of throwing
    }

    if (!_encryptionService.isSessionActive) {
      await _performHandshake();
    }

    // Log request start
    debugPrint('📡 [UnifiedApiClient] Starting $method request to: $endpoint');

    final headers = await _buildHeaders(skipTokenRefresh: skipTokenRefresh);
    final requestData = data != null 
        ? _encryptionService.createEncryptedRequest(data) 
        : _encryptionService.createEncryptedRequest({});

    try {
      final response = await _dio!.request(
        endpoint,
        data: requestData,
        options: Options(
          method: method,
          headers: headers,
          receiveTimeout: const Duration(seconds: 120),
          sendTimeout: const Duration(seconds: 120),
        ),
      );

      debugPrint('📡 [UnifiedApiClient] Response status: ${response.statusCode}');

      // Handle specific status codes manually since we disabled Dio's automatic throwing
      if (response.statusCode == 401 && !skipTokenRefresh) {
        debugPrint('🔄 [UnifiedApiClient] 401 Unauthorized - resetting encryption session');
        AICOLog.warn('401 Unauthorized - resetting encryption session',
          topic: 'network/request/encryption_session_reset',
          extra: {'endpoint': endpoint, 'method': method});
        
        // Reset encryption session since backend likely lost it
        _encryptionService.resetSession();
        
        // Retry the request once with new session
        try {
          debugPrint('🔄 [UnifiedApiClient] Retrying request after session reset');
          return await _makeEncryptedRequest<T>(
            method,
            endpoint,
            data: data,
            fromJson: fromJson,
            skipTokenRefresh: true, // Skip token refresh on retry to avoid infinite loop
          );
        } catch (retryError) {
          debugPrint('💥 [UnifiedApiClient] Retry after session reset failed: $retryError');
          return null;
        }
      }

      if (response.statusCode == 422) {
        debugPrint('⚠️ [UnifiedApiClient] 422 Validation error - handling gracefully');
        AICOLog.warn('Validation error from server', 
          topic: 'network/request/validation_error',
          extra: {
            'method': method,
            'endpoint': endpoint,
            'status_code': response.statusCode,
            'response_data': response.data
          });
        return null;
      }

      if (response.statusCode! >= 400) {
        debugPrint('❌ [UnifiedApiClient] Client error: ${response.statusCode}');
        AICOLog.error('Client error response', 
          topic: 'network/request/client_error',
          extra: {
            'method': method,
            'endpoint': endpoint,
            'status_code': response.statusCode,
            'response_data': response.data
          });
        return null;
      }

      // Success response
      debugPrint('✅ [UnifiedApiClient] Request successful: ${response.statusCode}');
      
      if (response.data != null && response.data is Map<String, dynamic>) {
        if (response.data['encrypted'] == true && response.data.containsKey('payload')) {
          final decryptedData = _encryptionService.decryptPayload(response.data['payload']);
          return _processResponse<T>(decryptedData, fromJson);
        }
      }
      
      return _processResponse<T>(response.data, fromJson);
    } on DioException catch (e) {
      debugPrint('🚨 [UnifiedApiClient] Dio exception caught: ${e.type} - Status: ${e.response?.statusCode}');
      
      // Handle timeout exceptions specifically
      if (e.type == DioExceptionType.receiveTimeout || 
          e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.sendTimeout) {
        debugPrint('⏰ [UnifiedApiClient] Request timeout - likely backend not running');
        AICOLog.warn('Request timeout - backend may not be available',
          topic: 'network/request/timeout',
          extra: {
            'method': method,
            'endpoint': endpoint,
            'timeout_type': e.type.toString(),
            'duration': '${_defaultTimeout.inSeconds}s'
          });
        return null;
      }
      
      // Handle connection errors
      if (e.type == DioExceptionType.connectionError) {
        debugPrint('🔌 [UnifiedApiClient] Connection error - backend not reachable');
        AICOLog.warn('Connection error - backend not reachable',
          topic: 'network/request/connection_error',
          extra: {
            'method': method,
            'endpoint': endpoint,
            'error': e.message
          });
        return null;
      }
      
      // Handle 401 errors - reset encryption session and retry once
      if (e.response?.statusCode == 401 && !skipTokenRefresh) {
        debugPrint('🔄 [UnifiedApiClient] 401 Unauthorized - resetting encryption session');
        AICOLog.warn('401 Unauthorized - resetting encryption session',
          topic: 'network/request/encryption_session_reset',
          extra: {'endpoint': endpoint, 'method': method});
        
        // Reset encryption session since backend likely lost it
        _encryptionService.resetSession();
        
        // Retry the request once with new session
        try {
          debugPrint('🔄 [UnifiedApiClient] Retrying request after session reset');
          return await _makeEncryptedRequest<T>(
            method,
            endpoint,
            data: data,
            fromJson: fromJson,
            skipTokenRefresh: true, // Skip token refresh on retry to avoid infinite loop
          );
        } catch (retryError) {
          debugPrint('💥 [UnifiedApiClient] Retry after session reset failed: $retryError');
          return null;
        }
      }
      
      // Handle 422 errors gracefully (validation errors)
      if (e.response?.statusCode == 422) {
        debugPrint('⚠️ [UnifiedApiClient] 422 Validation error - handling gracefully');
        AICOLog.warn('Validation error from server', 
          topic: 'network/request/validation_error',
          extra: {
            'method': method,
            'endpoint': endpoint,
            'status_code': e.response?.statusCode,
            'response_data': e.response?.data
          });
        return null;
      }
      
      debugPrint('❌ [UnifiedApiClient] Request failed: ${e.response?.statusCode} - ${e.message}');
      AICOLog.error('Encrypted request failed', 
        topic: 'network/request/encrypted_error',
        extra: {
          'method': method,
          'endpoint': endpoint,
          'status_code': e.response?.statusCode,
          'error': e.toString()
        });
      
      // Convert to custom exception but don't re-throw - return null instead
      final customException = _convertDioException(e);
      debugPrint('🔄 [UnifiedApiClient] Converted to: ${customException.runtimeType}');
      return null;
    } catch (e) {
      debugPrint('💥 [UnifiedApiClient] Unexpected error: $e');
      AICOLog.error('Unexpected error in encrypted request', 
        topic: 'network/request/unexpected_error',
        extra: {
          'method': method,
          'endpoint': endpoint,
          'error': e.toString()
        });
      return null; // Return null instead of rethrowing
    }
  }



  /// Convenience method for GET requests
  Future<T?> get<T>(String endpoint, {Map<String, dynamic>? queryParameters}) async {
    return _connectionManager.executeWithRetry(() => 
      _makeEncryptedRequest<T>('GET', endpoint, data: queryParameters)
    );
  }

  Future<T?> post<T>(String endpoint, {Map<String, dynamic>? data}) async {
    return _connectionManager.executeWithRetry(() => 
      request<T>('POST', endpoint, data: data)
    );
  }

  Future<T?> put<T>(String endpoint, {Map<String, dynamic>? data}) async {
    return _connectionManager.executeWithRetry(() => 
      _makeEncryptedRequest<T>('PUT', endpoint, data: data)
    );
  }

  Future<T?> delete<T>(String endpoint) async {
    return _connectionManager.executeWithRetry(() => 
      _makeEncryptedRequest<T>('DELETE', endpoint)
    );
  }

  /// Special method for token refresh that bypasses token validation
  Future<Map<String, dynamic>?> postForTokenRefresh(String endpoint, {Map<String, dynamic>? data}) async {
    debugPrint('🔄 [UnifiedApiClient] Token refresh request to: $endpoint');
    
    // Check if we're offline
    if (!_connectionManager.isOnline) {
      debugPrint('📱 [UnifiedApiClient] Device offline - cannot refresh token');
      return null;
    }

    if (!_encryptionService.isSessionActive) {
      await _performHandshake();
    }

    // Build headers WITHOUT token refresh check (skipTokenRefresh: true)
    final headers = await _buildHeaders(skipTokenRefresh: true);
    final requestData = data != null 
        ? _encryptionService.createEncryptedRequest(data) 
        : _encryptionService.createEncryptedRequest({});

    try {
      final response = await _dio!.request(
        endpoint,
        data: requestData,
        options: Options(
          method: 'POST',
          headers: headers,
        ),
      );

      debugPrint('📡 [UnifiedApiClient] Token refresh response status: ${response.statusCode}');

      // Handle specific status codes for token refresh
      if (response.statusCode == 401) {
        debugPrint('❌ [UnifiedApiClient] Token refresh failed - 401 Unauthorized');
        return null;
      }

      if (response.statusCode == 422) {
        debugPrint('⚠️ [UnifiedApiClient] Token refresh validation error - 422');
        return null;
      }

      if (response.statusCode! >= 400) {
        debugPrint('❌ [UnifiedApiClient] Token refresh client error: ${response.statusCode}');
        return null;
      }

      // Success response - process normally
      if (response.data != null && response.data is Map<String, dynamic>) {
        if (response.data['encrypted'] == true && response.data.containsKey('payload')) {
          final decryptedData = _encryptionService.decryptPayload(response.data['payload']);
          debugPrint('✅ [UnifiedApiClient] Token refresh successful (encrypted)');
          return decryptedData as Map<String, dynamic>?;
        }
        debugPrint('✅ [UnifiedApiClient] Token refresh successful (unencrypted)');
        return response.data as Map<String, dynamic>?;
      }
      
      return null;
    } on DioException catch (e) {
      debugPrint('🚨 [UnifiedApiClient] Token refresh Dio exception: ${e.type} - Status: ${e.response?.statusCode}');
      
      AICOLog.error('Token refresh request failed', 
        topic: 'network/request/token_refresh_error',
        extra: {
          'endpoint': endpoint,
          'status_code': e.response?.statusCode,
          'error': e.toString()
        });
      
      return null;
    } catch (e) {
      debugPrint('💥 [UnifiedApiClient] Token refresh unexpected error: $e');
      AICOLog.error('Unexpected error in token refresh request', 
        topic: 'network/request/token_refresh_unexpected_error',
        extra: {
          'endpoint': endpoint,
          'error': e.toString()
        });
      return null;
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
    };

    if (!skipTokenRefresh) {
      final tokenFresh = await _tokenManager.ensureTokenFreshness();
      if (!tokenFresh) {
        AICOLog.info('Token freshness check failed',
          topic: 'network/request/token_freshness_failed');
      }
    }
    
    final token = await _tokenManager.getValidToken();
    if (token != null) {
      headers['Authorization'] = 'Bearer $token';
    } else {
      AICOLog.warn('No valid token available for request',
        topic: 'network/request/no_token');
    }

    return headers;
  }


  /// Convert DioException to appropriate exception type
  Exception _convertDioException(DioException e) {
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return const ConnectionException('Request timeout');
      case DioExceptionType.connectionError:
        return const ConnectionException('Connection failed');
      case DioExceptionType.badResponse:
        if (e.response?.statusCode == 401) {
          return const AuthException('Authentication failed', statusCode: 401);
        } else if (e.response?.statusCode == 403) {
          return const AuthException('Access denied', statusCode: 403);
        } else if (e.response?.statusCode != null && e.response!.statusCode! >= 500) {
          return const ServerException('Server error'); // Return instead of throw
        }
        return HttpException('HTTP ${e.response?.statusCode}: ${e.response?.statusMessage}', statusCode: e.response?.statusCode ?? 0);
      case DioExceptionType.cancel:
        return const ConnectionException('Request cancelled');
      case DioExceptionType.unknown:
      default:
        return ConnectionException('Network error: ${e.message}');
    }
  }


  /// Dispose of resources
  Future<void> dispose() async {
    _dio?.close();
  }
}
