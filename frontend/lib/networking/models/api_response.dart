import 'package:json_annotation/json_annotation.dart';

part 'api_response.g.dart';

/// Generic wrapper for all API responses
@JsonSerializable(genericArgumentFactories: true)
class ApiResponse<T> {
  final bool success;
  final T? data;
  final String? error;
  final String? message;

  const ApiResponse({
    required this.success,
    this.data,
    this.error,
    this.message,
  });

  factory ApiResponse.fromJson(
    Map<String, dynamic> json,
    T Function(Object? json) fromJsonT,
  ) =>
      _$ApiResponseFromJson(json, fromJsonT);

  Map<String, dynamic> toJson(Object Function(T value) toJsonT) =>
      _$ApiResponseToJson(this, toJsonT);

  factory ApiResponse.success(T data, {String? message}) => ApiResponse(
        success: true,
        data: data,
        message: message,
      );

  factory ApiResponse.error(String error, {String? message}) => ApiResponse(
        success: false,
        error: error,
        message: message,
      );
}
