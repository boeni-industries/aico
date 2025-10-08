import 'package:aico_frontend/domain/entities/message.dart';

/// Abstract repository interface for message operations
abstract class MessageRepository {
  /// Send a new message
  Future<Message> sendMessage(Message message);
  
  /// Get messages for a conversation
  Future<List<Message>> getMessages(
    String conversationId, {
    int? limit,
    String? beforeMessageId,
  });
  
  /// Get message by ID
  Future<Message?> getMessageById(String id);
  
  /// Update message status
  Future<Message> updateMessageStatus(String messageId, MessageStatus status);
  
  /// Delete message
  Future<void> deleteMessage(String messageId);
  
  /// Mark message as read
  Future<void> markAsRead(String messageId);
  
  /// Get unread message count
  Future<int> getUnreadCount(String conversationId);
  
  /// Search messages
  Future<List<Message>> searchMessages(
    String query, {
    String? conversationId,
    int? limit,
  });
}
