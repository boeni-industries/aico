import 'package:aico_frontend/domain/entities/message.dart';
import 'package:aico_frontend/domain/repositories/message_repository.dart';

/// Use case for sending messages with validation and business logic
class SendMessageUseCase {
  final MessageRepository _messageRepository;

  const SendMessageUseCase(this._messageRepository);

  Future<Message> call(SendMessageParams params) async {
    // Validate message content
    if (params.content.trim().isEmpty) {
      throw ArgumentError('Message content cannot be empty');
    }

    if (params.content.length > 10000) {
      throw ArgumentError('Message content exceeds maximum length');
    }

    // Create message entity
    final message = Message(
      id: '', // Will be assigned by backend
      content: params.content.trim(),
      userId: params.userId,
      conversationId: params.conversationId,
      type: params.type,
      status: MessageStatus.draft,
      timestamp: DateTime.now(),
      metadata: params.metadata,
    );

    // Send through repository
    return await _messageRepository.sendMessage(message);
  }
}

class SendMessageParams {
  final String content;
  final String userId;
  final String conversationId;
  final MessageType type;
  final Map<String, dynamic>? metadata;

  const SendMessageParams({
    required this.content,
    required this.userId,
    required this.conversationId,
    this.type = MessageType.text,
    this.metadata,
  });
}
