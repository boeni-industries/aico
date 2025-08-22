import 'package:json_annotation/json_annotation.dart';

part 'error_models.g.dart';

/// Base class for all network-related exceptions
abstract class NetworkException implements Exception {
  final String message;
  final int? statusCode;
  final dynamic originalError;

  const NetworkException(this.message, {this.statusCode, this.originalError});

  @override
  String toString() => 'NetworkException: $message';
}

/// Connection-related errors
class ConnectionException extends NetworkException {
  const ConnectionException(String message, {dynamic originalError})
      : super(message, originalError: originalError);
}

/// HTTP-specific errors
class HttpException extends NetworkException {
  const HttpException(String message, int statusCode, {dynamic originalError})
      : super(message, statusCode: statusCode, originalError: originalError);
}

/// Authentication/authorization errors
class AuthException extends NetworkException {
  const AuthException(String message, {int? statusCode, dynamic originalError})
      : super(message, statusCode: statusCode, originalError: originalError);
}

/// Server-side errors
class ServerException extends NetworkException {
  const ServerException(String message, {int? statusCode, dynamic originalError})
      : super(message, statusCode: statusCode, originalError: originalError);
}

/// WebSocket-specific errors
class WebSocketException extends NetworkException {
  const WebSocketException(String message, {dynamic originalError})
      : super(message, originalError: originalError);
}

/// Offline/connectivity errors
class OfflineException extends NetworkException {
  const OfflineException(String message) : super(message);
}

/// API error response model
@JsonSerializable()
class ApiError {
  final String code;
  final String message;
  final String? details;
  final Map<String, dynamic>? metadata;

  const ApiError({
    required this.code,
    required this.message,
    this.details,
    this.metadata,
  });

  factory ApiError.fromJson(Map<String, dynamic> json) =>
      _$ApiErrorFromJson(json);

  Map<String, dynamic> toJson() => _$ApiErrorToJson(this);
}
