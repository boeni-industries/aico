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
    super.thinking,
  });

  factory MessageModel.fromJson(Map<String, dynamic> json) {
    // Backend sends 'role' field ('user' or 'assistant')
    // For AI messages (role=assistant), use 'aico' as userId for proper UI formatting
    final role = json['role'] as String? ?? 'user';
    final backendUserId = json['user_id'] as String;
    final actualUserId = role == 'assistant' ? 'aico' : backendUserId;
    
    return MessageModel(
      id: json['message_id'] as String? ?? json['id'] as String, // Use message_id from backend, fallback to id
      content: json['content'] as String,
      userId: actualUserId, // Use 'aico' for assistant messages, actual user_id for user messages
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
      thinking: json['thinking'] as String?,
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
      if (thinking != null) 'thinking': thinking,
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
      thinking: message.thinking,
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
      thinking: thinking,
    );
  }
}
