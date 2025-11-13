import 'dart:async';
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
  Future<Message> sendMessage(Message message, {bool stream = false}) async {
    if (stream) {
      // Use streaming logic - this will be handled by the provider
      throw UnimplementedError('Use sendMessageStreaming() for streaming');
    }
    try {
      final response = await _apiClient.request<Map<String, dynamic>>(
        'POST',
        '/conversation/messages',
        data: {
          'message': message.content,
          'message_type': 'text',
          'conversation_id': message.conversationId,
          'context': {
            'frontend_client': 'flutter',
          },
          'metadata': message.metadata ?? {},
        },
      );

      if (response != null) {
        final sentMessage = Message(
          id: response['message_id'] as String,
          content: message.content,
          userId: message.userId,
          conversationId: response['conversation_id'] as String,
          type: message.type,
          status: MessageStatus.sent,
          timestamp: message.timestamp,
          metadata: {
            'conversation_action': response['conversation_action'] as String,
            'conversation_reasoning': response['conversation_reasoning'] as String,
            'backend_status': response['status'] as String,
            'ai_response': response['ai_response'] as String?,
            'backend_timestamp': response['timestamp'] as String,
          },
        );

        return sentMessage;
      } else {
        AICOLog.warn('Message send failed: backend unavailable',
          topic: 'message_repository/send_backend_unavailable',
          extra: {
            'message_id': message.id,
            'conversation_id': message.conversationId,
          });

        return Message(
          id: message.id,
          content: message.content,
          userId: message.userId,
          conversationId: message.conversationId,
          type: message.type,
          status: MessageStatus.failed,
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

  /// Send message with streaming response
  Future<void> sendMessageStreaming(
    Message message,
    Function(String chunk, {String? contentType}) onChunk,
    Function(String finalResponse, {String? thinking}) onComplete,
    Function(String error) onError, {
    Function(String conversationId)? onConversationId,
    Function(String messageId)? onMessageId,  // Callback to pass backend message_id
  }) async {
    try {
      String? backendConversationId;

      final requestData = {
        'message': message.content,
        'message_type': 'text',
        'conversation_id': message.conversationId,
        'context': {
          'frontend_client': 'flutter',
        },
        'metadata': message.metadata ?? {},
      };

      String accumulatedContent = '';
      String accumulatedThinking = '';
      String? backendMessageId;

      await _apiClient.requestStream(
        'POST',
        '/conversation/messages',
        data: requestData,
        queryParameters: {'stream': 'true'},
        onHeaders: (Map<String, List<String>> headers) {
          if (headers.containsKey('x-conversation-id')) {
            backendConversationId = headers['x-conversation-id']!.first;
          }
        },
        onChunk: (Map<String, dynamic> chunkData) {
          final chunk = chunkData['content'] as String? ?? '';
          final contentType = chunkData['content_type'] as String? ?? 'response';
          
          // Extract message_id from final chunk
          if (chunkData['done'] == true) {
            print('📝 [REPOSITORY] Final chunk received: done=${chunkData['done']}, has_message_id=${chunkData.containsKey('message_id')}');
            if (chunkData.containsKey('message_id')) {
              backendMessageId = chunkData['message_id'] as String?;
              print('📝 [REPOSITORY] Extracted backend message_id: $backendMessageId');
              
              // Notify caller of backend message_id
              if (backendMessageId != null && onMessageId != null) {
                onMessageId(backendMessageId!);
              }
            } else {
              print('📝 [REPOSITORY] ❌ Final chunk does NOT contain message_id! Keys: ${chunkData.keys}');
            }
          }

          if (contentType == 'thinking') {
            accumulatedThinking += chunk;
          } else {
            accumulatedContent += chunk;
          }

          onChunk(chunk, contentType: contentType);
        },
        onComplete: () {
          if (backendConversationId != null && onConversationId != null) {
            onConversationId(backendConversationId!);
          }
          
          // Update message ID if backend provided one
          if (backendMessageId != null) {
            message = message.copyWith(id: backendMessageId!);
          }

          onComplete(accumulatedContent, thinking: accumulatedThinking.isNotEmpty ? accumulatedThinking : null);
        },
        onError: (String error) {
          AICOLog.error('Streaming failed',
            topic: 'message_repository/streaming_error',
            error: error,
            extra: {'message_id': message.id});
          onError(error);
        },
      );
    } catch (e) {
      AICOLog.error('Streaming request failed',
        topic: 'message_repository/streaming_http_error',
        error: e,
        extra: {'message_id': message.id});
      onError('Streaming request failed: ${e.toString()}');
    }
  }

  /// Get messages for a conversation
  @override
  Future<List<Message>> getMessages(String conversationId, {int? limit, String? beforeMessageId}) async {
    try {
      final queryParams = <String, String>{
        'page': '1',
        if (limit != null) 'page_size': limit.toString(),
        if (beforeMessageId != null) 'before': beforeMessageId,
      };

      // Use user-scoped endpoint - backend handles conversation filtering via auth
      final response = await _apiClient.request<Map<String, dynamic>>(
        'GET',
        '/conversation/messages',
        queryParameters: queryParams,
      );

      if (response != null) {
        final messagesData = response['messages'] as List<dynamic>? ?? [];
        
        final messages = messagesData
            .map((json) => MessageModel.fromJson(json as Map<String, dynamic>))
            .map((model) => model.toEntity())
            .toList();

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
