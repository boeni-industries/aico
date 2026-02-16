// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'interaction_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

InteractionRequest _$InteractionRequestFromJson(Map<String, dynamic> json) =>
    InteractionRequest(
      interactionId: json['interaction_id'] as String,
      userId: json['user_id'] as String,
      correlationId: json['correlation_id'] as String,
      interactionType: json['interaction_type'] as String,
      status: json['status'] as String,
      prompt: json['prompt'] as String,
      title: json['title'] as String?,
      requirement: json['requirement'] as String,
      severity: json['severity'] as String,
      category: json['category'] as String?,
      expectedAnswerType: json['expected_answer_type'] as String?,
      allowedOptions: (json['allowed_options'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      answerText: json['answer_text'] as String?,
      answerJson: json['answer_json'] as Map<String, dynamic>?,
      answeredAt: json['answered_at'] as String?,
      expiresAt: json['expires_at'] as String?,
      idempotencyKey: json['idempotency_key'] as String,
      createdAt: json['created_at'] as String,
      updatedAt: json['updated_at'] as String,
    );

Map<String, dynamic> _$InteractionRequestToJson(InteractionRequest instance) =>
    <String, dynamic>{
      'interaction_id': instance.interactionId,
      'user_id': instance.userId,
      'correlation_id': instance.correlationId,
      'interaction_type': instance.interactionType,
      'status': instance.status,
      'prompt': instance.prompt,
      'title': instance.title,
      'requirement': instance.requirement,
      'severity': instance.severity,
      'category': instance.category,
      'expected_answer_type': instance.expectedAnswerType,
      'allowed_options': instance.allowedOptions,
      'answer_text': instance.answerText,
      'answer_json': instance.answerJson,
      'answered_at': instance.answeredAt,
      'expires_at': instance.expiresAt,
      'idempotency_key': instance.idempotencyKey,
      'created_at': instance.createdAt,
      'updated_at': instance.updatedAt,
    };

InteractionEvent _$InteractionEventFromJson(Map<String, dynamic> json) =>
    InteractionEvent(
      eventId: json['event_id'] as String,
      interactionId: json['interaction_id'] as String,
      userId: json['user_id'] as String,
      correlationId: json['correlation_id'] as String,
      actor: json['actor'] as String,
      eventType: json['event_type'] as String,
      fromStatus: json['from_status'] as String?,
      toStatus: json['to_status'] as String?,
      payloadJson: json['payload_json'] as Map<String, dynamic>?,
      createdAt: json['created_at'] as String,
    );

Map<String, dynamic> _$InteractionEventToJson(InteractionEvent instance) =>
    <String, dynamic>{
      'event_id': instance.eventId,
      'interaction_id': instance.interactionId,
      'user_id': instance.userId,
      'correlation_id': instance.correlationId,
      'actor': instance.actor,
      'event_type': instance.eventType,
      'from_status': instance.fromStatus,
      'to_status': instance.toStatus,
      'payload_json': instance.payloadJson,
      'created_at': instance.createdAt,
    };

InteractionBroadcastData _$InteractionBroadcastDataFromJson(
  Map<String, dynamic> json,
) => InteractionBroadcastData(
  interaction: InteractionRequest.fromJson(
    json['interaction'] as Map<String, dynamic>,
  ),
  event: InteractionEvent.fromJson(json['event'] as Map<String, dynamic>),
);

Map<String, dynamic> _$InteractionBroadcastDataToJson(
  InteractionBroadcastData instance,
) => <String, dynamic>{
  'interaction': instance.interaction,
  'event': instance.event,
};

AnswerInteractionRequest _$AnswerInteractionRequestFromJson(
  Map<String, dynamic> json,
) => AnswerInteractionRequest(
  answerText: json['answer_text'] as String?,
  answerJson: json['answer_json'] as Map<String, dynamic>?,
);

Map<String, dynamic> _$AnswerInteractionRequestToJson(
  AnswerInteractionRequest instance,
) => <String, dynamic>{
  'answer_text': instance.answerText,
  'answer_json': instance.answerJson,
};
