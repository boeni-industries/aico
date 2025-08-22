// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'health_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

HealthResponse _$HealthResponseFromJson(Map<String, dynamic> json) =>
    HealthResponse(
      status: json['status'] as String,
      timestamp: json['timestamp'] as String,
    );

Map<String, dynamic> _$HealthResponseToJson(HealthResponse instance) =>
    <String, dynamic>{
      'status': instance.status,
      'timestamp': instance.timestamp,
    };

DetailedHealthResponse _$DetailedHealthResponseFromJson(
  Map<String, dynamic> json,
) => DetailedHealthResponse(
  status: json['status'] as String,
  timestamp: json['timestamp'] as String,
  version: json['version'] as String,
  components: json['components'] as Map<String, dynamic>,
  metrics: json['metrics'] as Map<String, dynamic>?,
);

Map<String, dynamic> _$DetailedHealthResponseToJson(
  DetailedHealthResponse instance,
) => <String, dynamic>{
  'status': instance.status,
  'timestamp': instance.timestamp,
  'version': instance.version,
  'components': instance.components,
  'metrics': instance.metrics,
};
