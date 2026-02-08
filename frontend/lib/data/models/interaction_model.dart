import 'package:json_annotation/json_annotation.dart';

part 'interaction_model.g.dart';

/// Interaction request model matching backend schema
@JsonSerializable()
class InteractionRequest {
  @JsonKey(name: 'interaction_id')
  final String interactionId;
  
  @JsonKey(name: 'user_id')
  final String userId;
  
  @JsonKey(name: 'correlation_id')
  final String correlationId;
  
  @JsonKey(name: 'interaction_type')
  final String interactionType;
  
  final String status;
  final String prompt;
  final String? title;
  final String requirement;
  final String severity;
  final String? category;
  
  @JsonKey(name: 'expected_answer_type')
  final String? expectedAnswerType;
  
  @JsonKey(name: 'allowed_options')
  final List<String>? allowedOptions;
  
  @JsonKey(name: 'answer_text')
  final String? answerText;
  
  @JsonKey(name: 'answer_json')
  final Map<String, dynamic>? answerJson;
  
  @JsonKey(name: 'answered_at')
  final String? answeredAt;
  
  @JsonKey(name: 'expires_at')
  final String? expiresAt;
  
  @JsonKey(name: 'idempotency_key')
  final String idempotencyKey;
  
  @JsonKey(name: 'created_at')
  final String createdAt;
  
  @JsonKey(name: 'updated_at')
  final String updatedAt;

  InteractionRequest({
    required this.interactionId,
    required this.userId,
    required this.correlationId,
    required this.interactionType,
    required this.status,
    required this.prompt,
    this.title,
    required this.requirement,
    required this.severity,
    this.category,
    this.expectedAnswerType,
    this.allowedOptions,
    this.answerText,
    this.answerJson,
    this.answeredAt,
    this.expiresAt,
    required this.idempotencyKey,
    required this.createdAt,
    required this.updatedAt,
  });

  factory InteractionRequest.fromJson(Map<String, dynamic> json) =>
      _$InteractionRequestFromJson(json);

  Map<String, dynamic> toJson() => _$InteractionRequestToJson(this);
}

/// Interaction event model for audit trail
@JsonSerializable()
class InteractionEvent {
  @JsonKey(name: 'event_id')
  final String eventId;
  
  @JsonKey(name: 'interaction_id')
  final String interactionId;
  
  @JsonKey(name: 'user_id')
  final String userId;
  
  @JsonKey(name: 'correlation_id')
  final String correlationId;
  
  final String actor;
  
  @JsonKey(name: 'event_type')
  final String eventType;
  
  @JsonKey(name: 'from_status')
  final String? fromStatus;
  
  @JsonKey(name: 'to_status')
  final String? toStatus;
  
  @JsonKey(name: 'payload_json')
  final Map<String, dynamic>? payloadJson;
  
  @JsonKey(name: 'created_at')
  final String createdAt;

  InteractionEvent({
    required this.eventId,
    required this.interactionId,
    required this.userId,
    required this.correlationId,
    required this.actor,
    required this.eventType,
    this.fromStatus,
    this.toStatus,
    this.payloadJson,
    required this.createdAt,
  });

  factory InteractionEvent.fromJson(Map<String, dynamic> json) =>
      _$InteractionEventFromJson(json);

  Map<String, dynamic> toJson() => _$InteractionEventToJson(this);
}

// Enums removed - using strings directly to match backend API

/// WebSocket broadcast data
@JsonSerializable()
class InteractionBroadcastData {
  final InteractionRequest interaction;
  final InteractionEvent event;

  InteractionBroadcastData({
    required this.interaction,
    required this.event,
  });

  factory InteractionBroadcastData.fromJson(Map<String, dynamic> json) =>
      _$InteractionBroadcastDataFromJson(json);

  Map<String, dynamic> toJson() => _$InteractionBroadcastDataToJson(this);
}

// WebSocket messages handled directly in service - no model needed

/// Answer request model
@JsonSerializable()
class AnswerInteractionRequest {
  @JsonKey(name: 'answer_text')
  final String? answerText;
  
  @JsonKey(name: 'answer_json')
  final Map<String, dynamic>? answerJson;

  AnswerInteractionRequest({
    this.answerText,
    this.answerJson,
  });

  factory AnswerInteractionRequest.fromJson(Map<String, dynamic> json) =>
      _$AnswerInteractionRequestFromJson(json);

  Map<String, dynamic> toJson() => _$AnswerInteractionRequestToJson(this);
}
