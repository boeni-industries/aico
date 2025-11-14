/// Modern Result pattern for API responses
/// Provides type-safe error handling with explicit success/failure states
library;

import 'package:aico_frontend/networking/exceptions/api_exceptions.dart';

/// Result type for API operations
/// Follows functional programming patterns for explicit error handling
sealed class ApiResult<T> {
  const ApiResult();
  
  /// Create a successful result
  const factory ApiResult.success(T data) = ApiSuccess<T>;
  
  /// Create a failure result
  const factory ApiResult.failure(ApiException error) = ApiFailure<T>;
  
  /// Check if the result is successful
  bool get isSuccess => this is ApiSuccess<T>;
  
  /// Check if the result is a failure
  bool get isFailure => this is ApiFailure<T>;
  
  /// Get the data if successful, null otherwise
  T? get data => switch (this) {
    ApiSuccess<T>(data: final data) => data,
    ApiFailure<T>() => null,
  };
  
  /// Get the error if failure, null otherwise
  ApiException? get error => switch (this) {
    ApiSuccess<T>() => null,
    ApiFailure<T>(error: final error) => error,
  };
  
  /// Transform the data if successful
  ApiResult<R> map<R>(R Function(T data) transform) => switch (this) {
    ApiSuccess<T>(data: final data) => ApiResult.success(transform(data)),
    ApiFailure<T>(error: final error) => ApiResult.failure(error),
  };
  
  /// Handle both success and failure cases
  R fold<R>(
    R Function(ApiException error) onFailure,
    R Function(T data) onSuccess,
  ) => switch (this) {
    ApiSuccess<T>(data: final data) => onSuccess(data),
    ApiFailure<T>(error: final error) => onFailure(error),
  };
  
  /// Execute side effects based on result
  ApiResult<T> when({
    void Function(T data)? onSuccess,
    void Function(ApiException error)? onFailure,
  }) {
    switch (this) {
      case ApiSuccess<T>(data: final data):
        onSuccess?.call(data);
      case ApiFailure<T>(error: final error):
        onFailure?.call(error);
    }
    return this;
  }
}

/// Successful API result
final class ApiSuccess<T> extends ApiResult<T> {
  const ApiSuccess(this.data);
  
  @override
  final T data;
  
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ApiSuccess<T> &&
          runtimeType == other.runtimeType &&
          data == other.data;
  
  @override
  int get hashCode => data.hashCode;
  
  @override
  String toString() => 'ApiSuccess(data: $data)';
}

/// Failed API result
final class ApiFailure<T> extends ApiResult<T> {
  const ApiFailure(this.error);
  
  @override
  final ApiException error;
  
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ApiFailure<T> &&
          runtimeType == other.runtimeType &&
          error == other.error;
  
  @override
  int get hashCode => error.hashCode;
  
  @override
  String toString() => 'ApiFailure(error: $error)';
}

/// Extension methods for easier Result handling
extension ApiResultExtensions<T> on ApiResult<T> {
  /// Get data or throw the error
  T getOrThrow() => switch (this) {
    ApiSuccess<T>(data: final data) => data,
    ApiFailure<T>(error: final error) => throw error,
  };
  
  /// Get data or return default value
  T getOrElse(T defaultValue) => switch (this) {
    ApiSuccess<T>(data: final data) => data,
    ApiFailure<T>() => defaultValue,
  };
  
  /// Get data or compute default value
  T getOrElseGet(T Function() defaultValue) => switch (this) {
    ApiSuccess<T>(data: final data) => data,
    ApiFailure<T>() => defaultValue(),
  };
}
