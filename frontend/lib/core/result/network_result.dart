/// Network-specific result types with business logic context
/// Extends the base ApiResult with network-aware error handling
library;

import 'package:aico_frontend/core/result/api_result.dart';
import 'package:aico_frontend/networking/exceptions/api_exceptions.dart';

/// Network result with retry and connection context
class NetworkResult<T> {
  const NetworkResult._(ApiResult<T> result, this.context) : _result = result;
  
  final ApiResult<T> _result;
  final NetworkContext context;
  
  /// Create successful network result
  factory NetworkResult.success(T data, {NetworkContext? context}) =>
      NetworkResult._(
        ApiResult.success(data),
        context ?? const NetworkContext(),
      );
  
  /// Create failed network result
  factory NetworkResult.failure(ApiException error, {NetworkContext? context}) =>
      NetworkResult._(
        ApiResult.failure(error),
        context ?? const NetworkContext(),
      );
  
  /// Create result from base ApiResult
  factory NetworkResult.fromApiResult(ApiResult<T> result, {NetworkContext? context}) =>
      NetworkResult._(result, context ?? const NetworkContext());
  
  bool get isSuccess => _result.isSuccess;
  
  bool get isFailure => _result.isFailure;
  
  T? get data => _result.data;
  
  ApiException? get error => _result.error;
  
  /// Check if this error should trigger a retry
  bool get shouldRetry => context.retryCount < context.maxRetries && 
      (error is ConnectionException || error is ServerException);
  
  /// Check if this error should trigger re-authentication
  bool get shouldReAuth => error is AuthException;
  
  /// Check if request was queued for offline processing
  bool get wasQueued => context.wasQueued;
  
  ApiResult<R> map<R>(R Function(T data) transform) =>
      _result.map(transform);
  
  R fold<R>(
    R Function(ApiException error) onFailure,
    R Function(T data) onSuccess,
  ) => _result.fold(onFailure, onSuccess);
  
  /// Create a new result with updated context
  NetworkResult<T> withContext(NetworkContext newContext) =>
      NetworkResult._(_result, newContext);
  
  /// Increment retry count
  NetworkResult<T> withRetry() =>
      withContext(context.copyWith(retryCount: context.retryCount + 1));
}

/// Context information for network operations
class NetworkContext {
  const NetworkContext({
    this.retryCount = 0,
    this.maxRetries = 3,
    this.wasQueued = false,
    this.endpoint,
    this.method,
    this.duration,
  });
  
  final int retryCount;
  final int maxRetries;
  final bool wasQueued;
  final String? endpoint;
  final String? method;
  final Duration? duration;
  
  NetworkContext copyWith({
    int? retryCount,
    int? maxRetries,
    bool? wasQueued,
    String? endpoint,
    String? method,
    Duration? duration,
  }) => NetworkContext(
    retryCount: retryCount ?? this.retryCount,
    maxRetries: maxRetries ?? this.maxRetries,
    wasQueued: wasQueued ?? this.wasQueued,
    endpoint: endpoint ?? this.endpoint,
    method: method ?? this.method,
    duration: duration ?? this.duration,
  );
}
