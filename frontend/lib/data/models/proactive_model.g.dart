// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'proactive_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

InitiationModel _$InitiationModelFromJson(Map<String, dynamic> json) =>
    InitiationModel(
      initiationId: json['initiation_id'] as String,
      userId: json['user_id'] as String,
      conversationId: json['conversation_id'] as String,
      question: json['question'] as String,
      initiatedAt: json['initiated_at'] as String,
      resolutionStatus: json['resolution_status'] as String,
      resolvedAt: json['resolved_at'] as String?,
      userResponseTime: (json['user_response_time'] as num?)?.toInt(),
      engagementScore: (json['engagement_score'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$InitiationModelToJson(InitiationModel instance) =>
    <String, dynamic>{
      'initiation_id': instance.initiationId,
      'user_id': instance.userId,
      'conversation_id': instance.conversationId,
      'question': instance.question,
      'initiated_at': instance.initiatedAt,
      'resolution_status': instance.resolutionStatus,
      'resolved_at': instance.resolvedAt,
      'user_response_time': instance.userResponseTime,
      'engagement_score': instance.engagementScore,
    };

InitiationResponseRequest _$InitiationResponseRequestFromJson(
  Map<String, dynamic> json,
) => InitiationResponseRequest(
  initiationId: json['initiation_id'] as String,
  responseType: json['response_type'] as String,
  responseText: json['response_text'] as String?,
  engagementScore: (json['engagement_score'] as num?)?.toDouble(),
);

Map<String, dynamic> _$InitiationResponseRequestToJson(
  InitiationResponseRequest instance,
) => <String, dynamic>{
  'initiation_id': instance.initiationId,
  'response_type': instance.responseType,
  'response_text': instance.responseText,
  'engagement_score': instance.engagementScore,
};
