import 'package:json_annotation/json_annotation.dart';

part 'admin_models.g.dart';

@JsonSerializable()
class AdminHealthResponse {
  final String status;
  final String timestamp;
  final String version;
  final Map<String, dynamic>? details;

  const AdminHealthResponse({
    required this.status,
    required this.timestamp,
    required this.version,
    this.details,
  });

  factory AdminHealthResponse.fromJson(Map<String, dynamic> json) =>
      _$AdminHealthResponseFromJson(json);
  Map<String, dynamic> toJson() => _$AdminHealthResponseToJson(this);
}

@JsonSerializable()
class GatewayStatusResponse {
  final String status;
  final Map<String, dynamic> adapters;
  final String uptime;
  final Map<String, dynamic>? metrics;

  const GatewayStatusResponse({
    required this.status,
    required this.adapters,
    required this.uptime,
    this.metrics,
  });

  factory GatewayStatusResponse.fromJson(Map<String, dynamic> json) =>
      _$GatewayStatusResponseFromJson(json);
  Map<String, dynamic> toJson() => _$GatewayStatusResponseToJson(this);
}

@JsonSerializable()
class LogEntry {
  final String timestamp;
  final String level;
  final String subsystem;
  final String message;
  final Map<String, dynamic>? metadata;

  const LogEntry({
    required this.timestamp,
    required this.level,
    required this.subsystem,
    required this.message,
    this.metadata,
  });

  factory LogEntry.fromJson(Map<String, dynamic> json) =>
      _$LogEntryFromJson(json);
  Map<String, dynamic> toJson() => _$LogEntryToJson(this);
}

@JsonSerializable()
class LogsListResponse {
  final List<LogEntry> logs;
  final int total;
  final int offset;
  final int limit;

  const LogsListResponse({
    required this.logs,
    required this.total,
    required this.offset,
    required this.limit,
  });

  factory LogsListResponse.fromJson(Map<String, dynamic> json) =>
      _$LogsListResponseFromJson(json);
  Map<String, dynamic> toJson() => _$LogsListResponseToJson(this);
}
