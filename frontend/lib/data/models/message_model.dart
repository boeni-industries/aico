import 'package:aico_frontend/domain/entities/message.dart';

/// Data model for Message entity with JSON serialization
class MessageModel extends Message {
  const MessageModel({
    required super.id,
    required super.content,
    required super.userId,
    required super.conversationId,
    required super.type,
    required super.status,
    required super.timestamp,
    super.metadata,
  });

  factory MessageModel.fromJson(Map<String, dynamic> json) {
    return MessageModel(
      id: json['id'] as String,
      content: json['content'] as String,
      userId: json['user_id'] as String,
      conversationId: json['conversation_id'] as String,
      type: MessageType.values.firstWhere(
        (e) => e.name == json['type'],
        orElse: () => MessageType.text,
      ),
      status: MessageStatus.values.firstWhere(
        (e) => e.name == json['status'],
        orElse: () => MessageStatus.sent,
      ),
      timestamp: DateTime.parse(json['timestamp'] as String),
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'content': content,
      'user_id': userId,
      'conversation_id': conversationId,
      'type': type.name,
      'status': status.name,
      'timestamp': timestamp.toIso8601String(),
      'metadata': metadata,
    };
  }

  factory MessageModel.fromEntity(Message message) {
    return MessageModel(
      id: message.id,
      content: message.content,
      userId: message.userId,
      conversationId: message.conversationId,
      type: message.type,
      status: message.status,
      timestamp: message.timestamp,
      metadata: message.metadata,
    );
  }

  Message toEntity() {
    return Message(
      id: id,
      content: content,
      userId: userId,
      conversationId: conversationId,
      type: type,
      status: status,
      timestamp: timestamp,
      metadata: metadata,
    );
  }
}
