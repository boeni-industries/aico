import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/data/models/message_model.dart';
import 'package:aico_frontend/domain/entities/message.dart';
import 'package:aico_frontend/domain/repositories/message_repository.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';

/// Implementation of MessageRepository that communicates with AICO backend
class MessageRepositoryImpl implements MessageRepository {
  final UnifiedApiClient _apiClient;

  const MessageRepositoryImpl(this._apiClient);

  @override
  Future<Message> sendMessage(Message message) async {
    try {
      AICOLog.info('Sending message to backend', 
        topic: 'message_repository/send',
        extra: {
          'message_id': message.id,
          'content_length': message.content.length,
          'conversation_id': message.conversationId,
        });

      // Convert domain entity to data model for API
      final messageModel = MessageModel.fromEntity(message);
      
      // Prepare request payload for backend /conversation/messages endpoint
      // Using UnifiedMessageRequest format matching backend schema
      final requestData = {
        'message': messageModel.content,
        'message_type': 'text', // Use literal string instead of enum
        'context': {
          'frontend_client': 'flutter',
          'conversation_id': messageModel.conversationId, // For context only
        },
        'metadata': messageModel.metadata ?? {},
      };

      // Send POST request to backend using UnifiedApiClient
      // This should never block UI - any auth issues will be handled asynchronously
      final response = await _apiClient.request<Map<String, dynamic>>(
        'POST',
        '/conversation/messages',
        data: requestData,
      );

      if (response != null) {
        // Backend returns UnifiedMessageResponse with fields:
        // success, message_id, thread_id, thread_action, status, timestamp, ai_response
        
        // Create a message entity from the backend response
        final sentMessage = Message(
          id: response['message_id'] as String,
          content: message.content, // Use original message content
          userId: message.userId,
          conversationId: response['thread_id'] as String,
          type: message.type,
          status: MessageStatus.sent, // Message was successfully sent
          timestamp: message.timestamp, // Keep original frontend timestamp
          metadata: {
            'thread_action': response['thread_action'] as String,
            'thread_reasoning': response['thread_reasoning'] as String,
            'backend_status': response['status'] as String,
            'ai_response': response['ai_response'] as String?, // Store AI response for later use
            'backend_timestamp': response['timestamp'] as String, // Store backend timestamp separately
          },
        );
        
        AICOLog.info('Message sent successfully', 
          topic: 'message_repository/send_success',
          extra: {
            'message_id': sentMessage.id,
            'conversation_id': sentMessage.conversationId,
            'thread_action': response['thread_action'],
            'has_ai_response': response.containsKey('ai_response') && response['ai_response'] != null,
          });

        return sentMessage;
      } else {
        // Handle null response gracefully - backend may be unavailable
        AICOLog.warn('Message send failed: backend unavailable', 
          topic: 'message_repository/send_backend_unavailable',
          extra: {
            'message_id': message.id,
            'conversation_id': message.conversationId,
          });
        
        // Return message with failed status instead of throwing
        return Message(
          id: message.id,
          content: message.content,
          userId: message.userId,
          conversationId: message.conversationId,
          type: message.type,
          status: MessageStatus.failed, // Mark as failed
          timestamp: message.timestamp,
          metadata: {
            'error': 'Backend unavailable',
            'retry_available': true,
          },
        );
      }
    } catch (e) {
      AICOLog.error('Failed to send message', 
        topic: 'message_repository/send_error',
        error: e,
        extra: {'message_id': message.id});
      
      // Return failed message instead of rethrowing
      return Message(
        id: message.id,
        content: message.content,
        userId: message.userId,
        conversationId: message.conversationId,
        type: message.type,
        status: MessageStatus.failed,
        timestamp: message.timestamp,
        metadata: {
          'error': e.toString(),
          'retry_available': true,
        },
      );
    }
  }

  @override
  Future<List<Message>> getMessages(
    String conversationId, {
    int? limit,
    String? beforeMessageId,
  }) async {
    try {
      AICOLog.info('Fetching messages from backend', 
        topic: 'message_repository/get_messages',
        extra: {
          'conversation_id': conversationId,
          'limit': limit,
          'before_message_id': beforeMessageId,
        });

      final queryParams = <String, String>{
        if (limit != null) 'page_size': limit.toString(),
        if (beforeMessageId != null) 'before': beforeMessageId,
      };

      final response = await _apiClient.request<Map<String, dynamic>>(
        'GET',
        '/conversations/threads/$conversationId/messages',
        queryParameters: queryParams,
      );

      if (response != null) {
        final messagesData = response['messages'] as List<dynamic>? ?? [];
        
        final messages = messagesData
            .map((json) => MessageModel.fromJson(json as Map<String, dynamic>))
            .map((model) => model.toEntity())
            .toList();

        AICOLog.info('Messages fetched successfully', 
          topic: 'message_repository/get_messages_success',
          extra: {
            'conversation_id': conversationId,
            'message_count': messages.length,
          });

        return messages;
      } else {
        throw Exception('Failed to fetch messages: null response');
      }
    } catch (e) {
      AICOLog.error('Failed to fetch messages', 
        topic: 'message_repository/get_messages_error',
        error: e,
        extra: {'conversation_id': conversationId});
      
      // Return empty list on error
      return [];
    }
  }

  @override
  Future<Message?> getMessageById(String id) async {
    try {
      // Note: Backend doesn't have individual message endpoint yet
      // This would need to be implemented when needed
      AICOLog.warn('getMessageById not implemented in backend', 
        topic: 'message_repository/get_by_id_not_implemented',
        extra: {'message_id': id});
      
      return null;
    } catch (e) {
      AICOLog.error('Failed to get message by ID', 
        topic: 'message_repository/get_by_id_error',
        error: e,
        extra: {'message_id': id});
      return null;
    }
  }

  @override
  Future<Message> updateMessageStatus(String messageId, MessageStatus status) async {
    try {
      // Note: Backend doesn't have message status update endpoint yet
      // For now, we'll just log and return a placeholder
      AICOLog.warn('updateMessageStatus not implemented in backend', 
        topic: 'message_repository/update_status_not_implemented',
        extra: {
          'message_id': messageId,
          'status': status.name,
        });
      
      // Return a placeholder message - this should be replaced when backend supports it
      throw UnimplementedError('Message status updates not yet supported by backend');
    } catch (e) {
      AICOLog.error('Failed to update message status', 
        topic: 'message_repository/update_status_error',
        error: e,
        extra: {
          'message_id': messageId,
          'status': status.name,
        });
      rethrow;
    }
  }

  @override
  Future<void> deleteMessage(String messageId) async {
    try {
      // Note: Backend doesn't have message deletion endpoint yet
      AICOLog.warn('deleteMessage not implemented in backend', 
        topic: 'message_repository/delete_not_implemented',
        extra: {'message_id': messageId});
      
      throw UnimplementedError('Message deletion not yet supported by backend');
    } catch (e) {
      AICOLog.error('Failed to delete message', 
        topic: 'message_repository/delete_error',
        error: e,
        extra: {'message_id': messageId});
      rethrow;
    }
  }

  @override
  Future<void> markAsRead(String messageId) async {
    try {
      // Note: Backend doesn't have mark as read endpoint yet
      AICOLog.warn('markAsRead not implemented in backend', 
        topic: 'message_repository/mark_read_not_implemented',
        extra: {'message_id': messageId});
      
      // For now, just log - implement when backend supports it
    } catch (e) {
      AICOLog.error('Failed to mark message as read', 
        topic: 'message_repository/mark_read_error',
        error: e,
        extra: {'message_id': messageId});
    }
  }

  @override
  Future<int> getUnreadCount(String conversationId) async {
    try {
      // Note: Backend doesn't have unread count endpoint yet
      AICOLog.warn('getUnreadCount not implemented in backend', 
        topic: 'message_repository/unread_count_not_implemented',
        extra: {'conversation_id': conversationId});
      
      return 0; // Return 0 for now
    } catch (e) {
      AICOLog.error('Failed to get unread count', 
        topic: 'message_repository/unread_count_error',
        error: e,
        extra: {'conversation_id': conversationId});
      return 0;
    }
  }

  @override
  Future<List<Message>> searchMessages(
    String query, {
    String? conversationId,
    int? limit,
  }) async {
    try {
      // Note: Backend doesn't have message search endpoint yet
      AICOLog.warn('searchMessages not implemented in backend', 
        topic: 'message_repository/search_not_implemented',
        extra: {
          'query': query,
          'conversation_id': conversationId,
          'limit': limit,
        });
      
      return []; // Return empty list for now
    } catch (e) {
      AICOLog.error('Failed to search messages', 
        topic: 'message_repository/search_error',
        error: e,
        extra: {
          'query': query,
          'conversation_id': conversationId,
        });
      return [];
    }
  }
}
