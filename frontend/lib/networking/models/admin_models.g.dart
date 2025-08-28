// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'admin_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

AdminHealthResponse _$AdminHealthResponseFromJson(Map<String, dynamic> json) =>
    AdminHealthResponse(
      status: json['status'] as String,
      timestamp: json['timestamp'] as String,
      version: json['version'] as String,
      details: json['details'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$AdminHealthResponseToJson(
  AdminHealthResponse instance,
) => <String, dynamic>{
  'status': instance.status,
  'timestamp': instance.timestamp,
  'version': instance.version,
  'details': instance.details,
};

GatewayStatusResponse _$GatewayStatusResponseFromJson(
  Map<String, dynamic> json,
) => GatewayStatusResponse(
  status: json['status'] as String,
  adapters: json['adapters'] as Map<String, dynamic>,
  uptime: json['uptime'] as String,
  metrics: json['metrics'] as Map<String, dynamic>?,
);

Map<String, dynamic> _$GatewayStatusResponseToJson(
  GatewayStatusResponse instance,
) => <String, dynamic>{
  'status': instance.status,
  'adapters': instance.adapters,
  'uptime': instance.uptime,
  'metrics': instance.metrics,
};

LogEntry _$LogEntryFromJson(Map<String, dynamic> json) => LogEntry(
  timestamp: json['timestamp'] as String,
  level: json['level'] as String,
  subsystem: json['subsystem'] as String,
  message: json['message'] as String,
  metadata: json['metadata'] as Map<String, dynamic>?,
);

Map<String, dynamic> _$LogEntryToJson(LogEntry instance) => <String, dynamic>{
  'timestamp': instance.timestamp,
  'level': instance.level,
  'subsystem': instance.subsystem,
  'message': instance.message,
  'metadata': instance.metadata,
};

LogsListResponse _$LogsListResponseFromJson(Map<String, dynamic> json) =>
    LogsListResponse(
      logs: (json['logs'] as List<dynamic>)
          .map((e) => LogEntry.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: (json['total'] as num).toInt(),
      offset: (json['offset'] as num).toInt(),
      limit: (json['limit'] as num).toInt(),
    );

Map<String, dynamic> _$LogsListResponseToJson(LogsListResponse instance) =>
    <String, dynamic>{
      'logs': instance.logs,
      'total': instance.total,
      'offset': instance.offset,
      'limit': instance.limit,
    };
