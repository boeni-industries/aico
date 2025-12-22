import 'package:json_annotation/json_annotation.dart';

part 'proactive_model.g.dart';

/// Model for proactive conversation initiation
@JsonSerializable()
class InitiationModel {
  @JsonKey(name: 'initiation_id')
  final String initiationId;
  
  @JsonKey(name: 'user_id')
  final String userId;
  
  @JsonKey(name: 'conversation_id')
  final String conversationId;
  
  final String question;
  
  @JsonKey(name: 'initiated_at')
  final String initiatedAt;
  
  @JsonKey(name: 'resolution_status')
  final String resolutionStatus;
  
  @JsonKey(name: 'resolved_at')
  final String? resolvedAt;
  
  @JsonKey(name: 'user_response_time')
  final int? userResponseTime;
  
  @JsonKey(name: 'engagement_score')
  final double? engagementScore;

  const InitiationModel({
    required this.initiationId,
    required this.userId,
    required this.conversationId,
    required this.question,
    required this.initiatedAt,
    required this.resolutionStatus,
    this.resolvedAt,
    this.userResponseTime,
    this.engagementScore,
  });

  factory InitiationModel.fromJson(Map<String, dynamic> json) =>
      _$InitiationModelFromJson(json);

  Map<String, dynamic> toJson() => _$InitiationModelToJson(this);
}

/// Request model for responding to proactive initiation
@JsonSerializable()
class InitiationResponseRequest {
  @JsonKey(name: 'initiation_id')
  final String initiationId;
  
  @JsonKey(name: 'response_type')
  final String responseType; // 'answered', 'dismissed', 'deferred'
  
  @JsonKey(name: 'response_text')
  final String? responseText;
  
  @JsonKey(name: 'engagement_score')
  final double? engagementScore;

  const InitiationResponseRequest({
    required this.initiationId,
    required this.responseType,
    this.responseText,
    this.engagementScore,
  });

  factory InitiationResponseRequest.fromJson(Map<String, dynamic> json) =>
      _$InitiationResponseRequestFromJson(json);

  Map<String, dynamic> toJson() => _$InitiationResponseRequestToJson(this);
}
