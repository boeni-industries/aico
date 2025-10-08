import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/networking/services/connection_manager.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';

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
       _connectionManager = connectionManager;

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
        validateStatus: (status) => status != null && status < 500,
      ));

      // Add logging interceptor
      _dio!.interceptors.add(LogInterceptor(
        request: true,
        requestHeader: true,
        requestBody: true,
        responseHeader: true,
        responseBody: true,
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

  /// Make streaming request with proper HTTP streaming support
  Future<void> requestStream(
    String method,
    String endpoint, {
    Map<String, dynamic>? data,
    Map<String, String>? queryParameters,
    required Function(String chunk) onChunk,
    required Function() onComplete,
    required Function(String error) onError,
    Function(Map<String, List<String>> headers)? onHeaders,
    bool skipTokenRefresh = false,
  }) async {
    AICOLog.info('🚀 STARTING STREAMING REQUEST', 
      topic: 'network/streaming/start',
      extra: {'method': method, 'endpoint': endpoint});
    
    // Auto-initialize if not done yet
    if (!_isInitialized) {
      await initialize();
    }

    try {
      // Build headers with authentication
      final headers = await _buildHeaders(skipTokenRefresh: skipTokenRefresh);
      
      // Check encryption session
      if (!_encryptionService.isSessionActive) {
        await _performHandshake();
      }

      // Prepare encrypted request data
      final requestData = data != null 
          ? _encryptionService.createEncryptedRequest(data) 
          : _encryptionService.createEncryptedRequest({});

      // Make streaming request using Dio
      AICOLog.info('📡 Making Dio streaming request', 
        topic: 'network/streaming/dio_request',
        extra: {'endpoint': endpoint, 'method': method});
      
      final response = await _dio!.request<ResponseBody>(
        endpoint,
        data: requestData,
        queryParameters: queryParameters,
        options: Options(
          method: method,
          headers: headers,
          responseType: ResponseType.stream, // Enable streaming response
        ),
      );

      AICOLog.info('📡 Dio response received', 
        topic: 'network/streaming/dio_response',
        extra: {'status_code': response.statusCode, 'has_data': response.data != null});

      // Extract and pass headers if callback provided
      if (onHeaders != null && response.headers.map.isNotEmpty) {
        onHeaders(response.headers.map);
      }
      
      if (response.statusCode == 200 && response.data != null) {
        // Handle streaming response
        AICOLog.info('🔄 Starting stream processing', 
          topic: 'network/streaming/stream_start');
        
        final stream = response.data!.stream;
        String buffer = '';
        
        await for (final chunkBytes in stream) {
          final chunk = utf8.decode(chunkBytes);
          AICOLog.info('📦 Raw chunk received', 
            topic: 'network/streaming/raw_chunk',
            extra: {'chunk_length': chunk.length, 'chunk_preview': chunk.length > 50 ? '${chunk.substring(0, 50)}...' : chunk});
          
          buffer += chunk;
          
          AICOLog.info('📋 Buffer updated', 
            topic: 'network/streaming/buffer_update',
            extra: {
              'buffer_length': buffer.length, 
              'newline_count': '\n'.allMatches(buffer).length,
              'buffer_preview': buffer.length > 100 ? '${buffer.substring(0, 100)}...' : buffer
            });
          
          // Process complete JSON objects (split on newlines)
          final lines = buffer.split('\n');
          
          // Keep the last line in buffer if it doesn't end with newline
          if (!buffer.endsWith('\n')) {
            buffer = lines.removeLast();
          } else {
            buffer = '';
          }
          
          AICOLog.info('📝 Lines split', 
            topic: 'network/streaming/lines_split',
            extra: {'lines_count': lines.length, 'remaining_buffer_length': buffer.length});
          
          for (final line in lines) {
            if (line.trim().isNotEmpty) {
              AICOLog.info('🔍 Processing line', 
                topic: 'network/streaming/line_process',
                extra: {'line_length': line.length, 'line_preview': line.length > 100 ? '${line.substring(0, 100)}...' : line});
              try {
                final jsonData = jsonDecode(line);
                AICOLog.info('✅ JSON parsed successfully', 
                  topic: 'network/streaming/json_parsed',
                  extra: {'has_encrypted': jsonData.containsKey('encrypted')});
                
                // ALL streaming responses MUST be encrypted per AICO security requirements
                if (jsonData.containsKey('encrypted') && jsonData['encrypted'] == true) {
                  AICOLog.info('Decrypting streaming chunk', 
                    topic: 'network/streaming/decrypt',
                    extra: {'payload_length': jsonData['payload']?.toString().length ?? 0});
                  
                  final decryptedData = _encryptionService.decryptPayload(jsonData['payload']);
                  
                  AICOLog.info('Decrypted streaming chunk', 
                    topic: 'network/streaming/decrypted',
                    extra: {
                      'type': decryptedData['type'],
                      'content_length': decryptedData['content']?.toString().length ?? 0,
                      'content_preview': decryptedData['content']?.toString().substring(0, 
                        (decryptedData['content']?.toString().length ?? 0) > 20 ? 20 : (decryptedData['content']?.toString().length ?? 0)) ?? ''
                    });
                  
                  if (decryptedData['type'] == 'chunk') {
                    final content = decryptedData['content'] ?? '';
                    AICOLog.info('Passing chunk to onChunk', 
                      topic: 'network/streaming/chunk_pass',
                      extra: {'content': content});
                    onChunk(content);
                  } else if (decryptedData['type'] == 'error') {
                    onError(decryptedData['error'] ?? 'Unknown streaming error');
                    return;
                  }
                } else {
                  // SECURITY VIOLATION: Unencrypted streaming response received
                  AICOLog.error('Security violation: Unencrypted streaming response received', 
                    topic: 'network/streaming/security_violation',
                    extra: {'response_type': jsonData['type'], 'full_data': jsonData});
                  onError('Security violation: Unencrypted streaming response');
                  return;
                }
              } catch (e) {
                AICOLog.warn('Failed to parse streaming chunk: $line', 
                  topic: 'network/streaming/parse_error',
                  extra: {'error': e.toString()});
              }
            }
          }
        }
        
        // Process any remaining buffer content
        if (buffer.trim().isNotEmpty) {
          try {
            final jsonData = jsonDecode(buffer);
            if (jsonData.containsKey('encrypted') && jsonData['encrypted'] == true) {
              final decryptedData = _encryptionService.decryptPayload(jsonData['payload']);
              if (decryptedData['type'] == 'chunk') {
                onChunk(decryptedData['content'] ?? '');
              }
            } else {
              // SECURITY VIOLATION: Final buffer chunk is unencrypted
              AICOLog.error('Security violation: Unencrypted final streaming chunk', 
                topic: 'network/streaming/security_violation');
            }
          } catch (e) {
            // Ignore final buffer parsing errors
          }
        }
        
        onComplete();
        
      } else {
        onError('HTTP ${response.statusCode}: ${response.statusMessage}');
      }
      
    } catch (e) {
      AICOLog.error('Streaming request failed', 
        topic: 'network/streaming/request_error',
        extra: {'method': method, 'endpoint': endpoint, 'error': e.toString()});
      onError('Streaming request failed: ${e.toString()}');
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
    debugPrint('📡 [UnifiedApiClient] Making encrypted request: $method $endpoint');

    try {
      // Build headers with authentication
      final headers = await _buildHeaders(skipTokenRefresh: skipTokenRefresh);

      // Prepare encrypted request data
      final requestData = data != null 
          ? _encryptionService.createEncryptedRequest(data) 
          : _encryptionService.createEncryptedRequest({});

      // Make the request
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
        AICOLog.warn('401 Unauthorized - will reset encryption session and retry',
          topic: 'network/request/unauthorized',
          extra: {'endpoint': endpoint, 'method': method});
        
        // Reset encryption session and retry once
        _encryptionService.resetSession();
        return await _makeEncryptedRequest<T>(
          method, 
          endpoint, 
          data: data, 
          fromJson: fromJson, 
          skipTokenRefresh: true
        );
      }

      if (response.statusCode != null && response.statusCode! >= 400) {
        debugPrint('❌ [UnifiedApiClient] HTTP error: ${response.statusCode}');
        AICOLog.warn('HTTP error response',
          topic: 'network/request/http_error',
          extra: {
            'status_code': response.statusCode,
            'endpoint': endpoint,
            'method': method,
            'response_data': response.data?.toString()
          });
        return null; // Return null instead of throwing for HTTP errors
      }

      // Process successful response
      return _processResponse<T>(response.data, fromJson);

    } on DioException catch (e) {
      return _handleDioException<T>(e, method, endpoint);
    } catch (e) {
      debugPrint('💥 [UnifiedApiClient] Unexpected error: $e');
      AICOLog.error('Unexpected error in API request',
        topic: 'network/request/unexpected_error',
        extra: {
          'method': method,
          'endpoint': endpoint,
          'error': e.toString()
        });
      return null;
    }
  }

  /// Handle DioException with proper error categorization
  T? _handleDioException<T>(DioException e, String method, String endpoint) {
    // Handle timeout errors
    if (e.type == DioExceptionType.receiveTimeout || 
        e.type == DioExceptionType.sendTimeout ||
        e.type == DioExceptionType.connectionTimeout) {
      debugPrint('⏱️ [UnifiedApiClient] Request timeout');
      AICOLog.warn('Request timeout',
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
    
    // Handle 401 errors - reset encryption session and retry
    if (e.response?.statusCode == 401) {
      debugPrint('🔐 [UnifiedApiClient] 401 Unauthorized - encryption session may be invalid');
      AICOLog.warn('401 Unauthorized - encryption session invalid',
        topic: 'network/request/unauthorized',
        extra: {
          'method': method,
          'endpoint': endpoint
        });
      return null;
    }
    
    // Handle other HTTP errors
    if (e.response?.statusCode != null) {
      debugPrint('❌ [UnifiedApiClient] HTTP ${e.response!.statusCode}: ${e.response!.statusMessage}');
      AICOLog.warn('HTTP error response',
        topic: 'network/request/http_error',
        extra: {
          'status_code': e.response!.statusCode,
          'status_message': e.response!.statusMessage,
          'method': method,
          'endpoint': endpoint
        });
      return null;
    }
    
    // Handle other errors
    debugPrint('💥 [UnifiedApiClient] Request failed: ${e.message}');
    AICOLog.error('Request failed',
      topic: 'network/request/failed',
      extra: {
        'method': method,
        'endpoint': endpoint,
        'error_type': e.type.toString(),
        'error_message': e.message
      });
    return null;
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

  /// Perform encryption handshake with backend
  Future<void> _performHandshake() async {
    final handshakeRequest = await _encryptionService.createHandshakeRequest();
    
    final response = await _dio!.post(
      '/handshake',
      data: handshakeRequest,
    );

    await _encryptionService.processHandshakeResponse(response.data);
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

    try {
      // Prepare encrypted request data
      final requestData = data != null 
          ? _encryptionService.createEncryptedRequest(data) 
          : _encryptionService.createEncryptedRequest({});

      final response = await _dio!.post(
        endpoint,
        data: requestData,
        options: Options(
          headers: headers,
          receiveTimeout: const Duration(seconds: 30),
          sendTimeout: const Duration(seconds: 30),
        ),
      );

      debugPrint('🔄 [UnifiedApiClient] Token refresh response: ${response.statusCode}');

      if (response.statusCode == 200) {
        return _processResponse<Map<String, dynamic>>(response.data, null);
      } else {
        debugPrint('❌ [UnifiedApiClient] Token refresh failed: ${response.statusCode}');
        return null;
      }

    } on DioException catch (e) {
      debugPrint('💥 [UnifiedApiClient] Token refresh DioException: ${e.type} - ${e.message}');
      
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

  /// Dispose of resources
  Future<void> dispose() async {
    _dio?.close();
  }
}
