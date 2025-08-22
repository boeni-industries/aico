import 'package:json_annotation/json_annotation.dart';

part 'health_models.g.dart';

@JsonSerializable()
class HealthResponse {
  final String status;
  final String timestamp;

  const HealthResponse({
    required this.status,
    required this.timestamp,
  });

  factory HealthResponse.fromJson(Map<String, dynamic> json) =>
      _$HealthResponseFromJson(json);
  Map<String, dynamic> toJson() => _$HealthResponseToJson(this);
}

@JsonSerializable()
class DetailedHealthResponse {
  final String status;
  final String timestamp;
  final String version;
  final Map<String, dynamic> components;
  final Map<String, dynamic>? metrics;

  const DetailedHealthResponse({
    required this.status,
    required this.timestamp,
    required this.version,
    required this.components,
    this.metrics,
  });

  factory DetailedHealthResponse.fromJson(Map<String, dynamic> json) =>
      _$DetailedHealthResponseFromJson(json);
  Map<String, dynamic> toJson() => _$DetailedHealthResponseToJson(this);
}
