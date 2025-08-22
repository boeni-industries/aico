import 'dart:convert';
import 'package:http/http.dart' as http;

/// HTTP API client with unified error handling and request/response patterns
/// Provides consistent API communication across all repositories
class ApiClient {
  final http.Client _httpClient;
  final String _baseUrl;
  final Map<String, String> _defaultHeaders;

  ApiClient({
    required http.Client httpClient,
    required String baseUrl,
    Map<String, String>? defaultHeaders,
  })  : _httpClient = httpClient,
        _baseUrl = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl,
        _defaultHeaders = {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...?defaultHeaders,
        };

  /// GET request with error handling
  Future<ApiResponse<T>> get<T>(
    String endpoint, {
    Map<String, String>? headers,
    Map<String, dynamic>? queryParams,
    T Function(Map<String, dynamic>)? fromJson,
  }) async {
    try {
      final uri = _buildUri(endpoint, queryParams);
      final response = await _httpClient.get(
        uri,
        headers: {..._defaultHeaders, ...?headers},
      );
      
      return _handleResponse<T>(response, fromJson);
    } catch (e) {
      throw ApiException('GET $endpoint failed: $e');
    }
  }

  /// POST request with error handling
  Future<ApiResponse<T>> post<T>(
    String endpoint, {
    Map<String, String>? headers,
    Map<String, dynamic>? body,
    T Function(Map<String, dynamic>)? fromJson,
  }) async {
    try {
      final uri = _buildUri(endpoint);
      final response = await _httpClient.post(
        uri,
        headers: {..._defaultHeaders, ...?headers},
        body: body != null ? jsonEncode(body) : null,
      );
      
      return _handleResponse<T>(response, fromJson);
    } catch (e) {
      throw ApiException('POST $endpoint failed: $e');
    }
  }

  /// PUT request with error handling
  Future<ApiResponse<T>> put<T>(
    String endpoint, {
    Map<String, String>? headers,
    Map<String, dynamic>? body,
    T Function(Map<String, dynamic>)? fromJson,
  }) async {
    try {
      final uri = _buildUri(endpoint);
      final response = await _httpClient.put(
        uri,
        headers: {..._defaultHeaders, ...?headers},
        body: body != null ? jsonEncode(body) : null,
      );
      
      return _handleResponse<T>(response, fromJson);
    } catch (e) {
      throw ApiException('PUT $endpoint failed: $e');
    }
  }

  /// DELETE request with error handling
  Future<ApiResponse<T>> delete<T>(
    String endpoint, {
    Map<String, String>? headers,
    T Function(Map<String, dynamic>)? fromJson,
  }) async {
    try {
      final uri = _buildUri(endpoint);
      final response = await _httpClient.delete(
        uri,
        headers: {..._defaultHeaders, ...?headers},
      );
      
      return _handleResponse<T>(response, fromJson);
    } catch (e) {
      throw ApiException('DELETE $endpoint failed: $e');
    }
  }

  /// Build URI with query parameters
  Uri _buildUri(String endpoint, [Map<String, dynamic>? queryParams]) {
    final url = '$_baseUrl$endpoint';
    if (queryParams != null && queryParams.isNotEmpty) {
      return Uri.parse(url).replace(queryParameters: 
        queryParams.map((key, value) => MapEntry(key, value.toString())));
    }
    return Uri.parse(url);
  }

  /// Handle HTTP response with unified error handling
  ApiResponse<T> _handleResponse<T>(
    http.Response response,
    T Function(Map<String, dynamic>)? fromJson,
  ) {
    final statusCode = response.statusCode;
    
    // Parse response body
    Map<String, dynamic>? responseData;
    try {
      if (response.body.isNotEmpty) {
        responseData = jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      throw ApiException('Failed to parse response JSON: $e');
    }

    // Handle different status codes
    if (statusCode >= 200 && statusCode < 300) {
      // Success
      T? data;
      if (fromJson != null && responseData != null) {
        try {
          data = fromJson(responseData);
        } catch (e) {
          throw ApiException('Failed to deserialize response: $e');
        }
      }
      
      return ApiResponse<T>(
        data: data,
        statusCode: statusCode,
        rawData: responseData,
        isSuccess: true,
      );
    } else {
      // Error
      final errorMessage = responseData?['message'] ?? 
                          responseData?['error'] ?? 
                          'HTTP $statusCode';
      
      throw ApiException(
        errorMessage,
        statusCode: statusCode,
        responseData: responseData,
      );
    }
  }

  /// Close the HTTP client
  void dispose() {
    _httpClient.close();
  }
}

/// API response wrapper
class ApiResponse<T> {
  final T? data;
  final int statusCode;
  final Map<String, dynamic>? rawData;
  final bool isSuccess;

  const ApiResponse({
    this.data,
    required this.statusCode,
    this.rawData,
    required this.isSuccess,
  });
}

/// API exception with detailed error information
class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final Map<String, dynamic>? responseData;

  const ApiException(
    this.message, {
    this.statusCode,
    this.responseData,
  });

  @override
  String toString() {
    if (statusCode != null) {
      return 'ApiException($statusCode): $message';
    }
    return 'ApiException: $message';
  }

  /// Check if error is network-related
  bool get isNetworkError => statusCode == null;
  
  /// Check if error is client-side (4xx)
  bool get isClientError => statusCode != null && statusCode! >= 400 && statusCode! < 500;
  
  /// Check if error is server-side (5xx)
  bool get isServerError => statusCode != null && statusCode! >= 500;
}
