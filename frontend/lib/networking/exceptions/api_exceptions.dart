/// API exception classes for networking layer
/// Follows AICO guidelines for clear error handling
library;

/// Base exception for all API-related errors
abstract class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final dynamic originalError;

  const ApiException(this.message, {this.statusCode, this.originalError});

  @override
  String toString() => 'ApiException: $message';
}

/// Thrown when device is offline
class OfflineException extends ApiException {
  const OfflineException(super.message);

  @override
  String toString() => 'OfflineException: $message';
}

/// Thrown when connection fails
class ConnectionException extends ApiException {
  const ConnectionException(super.message, {super.statusCode, super.originalError});

  @override
  String toString() => 'ConnectionException: $message';
}

/// Thrown when authentication fails
class AuthException extends ApiException {
  const AuthException(super.message, {super.statusCode, super.originalError});

  @override
  String toString() => 'AuthException: $message';
}

/// Thrown when server returns an error
class ServerException extends ApiException {
  const ServerException(super.message, {super.statusCode, super.originalError});

  @override
  String toString() => 'ServerException: $message';
}

/// Thrown for HTTP-related errors
class HttpException extends ApiException {
  const HttpException(super.message, {super.statusCode, super.originalError});

  @override
  String toString() => 'HttpException: $message';
}
