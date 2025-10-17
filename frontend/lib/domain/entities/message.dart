import 'package:equatable/equatable.dart';

/// Domain entity representing a conversation message
class Message extends Equatable {
  final String id;
  final String content;
  final String userId;
  final String conversationId;
  final MessageType type;
  final MessageStatus status;
  final DateTime timestamp;
  final Map<String, dynamic>? metadata;
  final String? thinking; // Inner monologue from <think> tags

  const Message({
    required this.id,
    required this.content,
    required this.userId,
    required this.conversationId,
    required this.type,
    required this.status,
    required this.timestamp,
    this.metadata,
    this.thinking,
  });

  @override
  List<Object?> get props => [
        id,
        content,
        userId,
        conversationId,
        type,
        status,
        timestamp,
        metadata,
        thinking,
      ];

  Message copyWith({
    String? id,
    String? content,
    String? userId,
    String? conversationId,
    MessageType? type,
    MessageStatus? status,
    DateTime? timestamp,
    Map<String, dynamic>? metadata,
    String? thinking,
  }) {
    return Message(
      id: id ?? this.id,
      content: content ?? this.content,
      userId: userId ?? this.userId,
      conversationId: conversationId ?? this.conversationId,
      type: type ?? this.type,
      status: status ?? this.status,
      timestamp: timestamp ?? this.timestamp,
      metadata: metadata ?? this.metadata,
      thinking: thinking ?? this.thinking,
    );
  }
}

enum MessageType {
  text,
  voice,
  image,
  file,
  system,
}

enum MessageStatus {
  draft,
  sending,
  sent,
  delivered,
  read,
  failed,
}

extension MessageStatusExtension on MessageStatus {
  bool get isSuccessful => this == MessageStatus.sent || 
                          this == MessageStatus.delivered || 
                          this == MessageStatus.read;
  
  bool get isPending => this == MessageStatus.draft || 
                       this == MessageStatus.sending;
  
  bool get hasError => this == MessageStatus.failed;
}
