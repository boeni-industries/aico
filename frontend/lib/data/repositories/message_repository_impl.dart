import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
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
        // success, message_id, conversation_id, conversation_action, status, timestamp, ai_response
        
        // Create a message entity from the backend response
        final sentMessage = Message(
          id: response['message_id'] as String,
          content: message.content, // Use original message content
          userId: message.userId,
          conversationId: response['conversation_id'] as String,
          type: message.type,
          status: MessageStatus.sent, // Message was successfully sent
          timestamp: message.timestamp, // Keep original frontend timestamp
          metadata: {
            'conversation_action': response['conversation_action'] as String,
            'conversation_reasoning': response['conversation_reasoning'] as String,
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
            'conversation_action': response['conversation_action'],
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

  /// Send message with streaming response
  Future<void> sendMessageStreaming(
    Message message, 
    Function(String chunk) onChunk,
    Function(String finalResponse) onComplete,
    Function(String error) onError,
  ) async {
    try {
      AICOLog.info('Starting streaming message send', 
        topic: 'message_repository/send_streaming',
        extra: {
          'message_id': message.id,
          'content_length': message.content.length,
          'conversation_id': message.conversationId,
        });

      // Prepare request payload
      final requestData = {
        'message': message.content,
        'message_type': 'text',
        'context': {
          'frontend_client': 'flutter',
          'conversation_id': message.conversationId,
        },
        'metadata': message.metadata ?? {},
      };

      // Use UnifiedApiClient's internal Dio instance for streaming
      // We'll need to access the base URL and build headers manually
      const baseUrl = 'http://localhost:8771/api/v1'; // Default base URL
      
      // Create streaming request to same endpoint with stream=true parameter
      final url = Uri.parse('$baseUrl/conversation/messages?stream=true');
      final request = http.Request('POST', url);
      
      // Add basic headers
      request.headers['Content-Type'] = 'application/json';
      
      // TODO: Add authentication header - for now, skip auth for streaming
      // This would need to be implemented properly with token management
      
      request.body = jsonEncode(requestData);

      // Send streaming request
      final response = await request.send();
      
      if (response.statusCode == 200) {
        String accumulatedContent = '';
        
        // Process streaming response
        await for (final chunk in response.stream.transform(utf8.decoder).transform(const LineSplitter())) {
          if (chunk.trim().isEmpty) continue;
          
          try {
            final chunkData = jsonDecode(chunk) as Map<String, dynamic>;
            final type = chunkData['type'] as String?;
            
            switch (type) {
              case 'metadata':
                AICOLog.info('Received streaming metadata', 
                  topic: 'message_repository/streaming_metadata',
                  extra: chunkData);
                break;
                
              case 'chunk':
                final content = chunkData['content'] as String? ?? '';
                final accumulated = chunkData['accumulated'] as String? ?? accumulatedContent + content;
                final isDone = chunkData['done'] as bool? ?? false;
                
                accumulatedContent = accumulated;
                onChunk(content);
                
                if (isDone) {
                  onComplete(accumulatedContent);
                  AICOLog.info('Streaming completed successfully', 
                    topic: 'message_repository/streaming_complete',
                    extra: {
                      'message_id': message.id,
                      'final_length': accumulatedContent.length,
                    });
                  return;
                }
                break;
                
              case 'error':
                final error = chunkData['error'] as String? ?? 'Unknown streaming error';
                onError(error);
                AICOLog.error('Streaming error received', 
                  topic: 'message_repository/streaming_error',
                  error: error,
                  extra: {'message_id': message.id});
                return;
            }
          } catch (e) {
            AICOLog.warn('Failed to parse streaming chunk', 
              topic: 'message_repository/streaming_parse_error',
              error: e,
              extra: {'chunk': chunk});
          }
        }
        
        // If we reach here without completion, it's an incomplete stream
        onError('Stream ended without completion');
        
      } else {
        final errorBody = await response.stream.bytesToString();
        onError('HTTP ${response.statusCode}: $errorBody');
        AICOLog.error('Streaming request failed', 
          topic: 'message_repository/streaming_http_error',
          error: 'HTTP ${response.statusCode}',
          extra: {
            'message_id': message.id,
            'status_code': response.statusCode,
            'error_body': errorBody,
          });
      }
      
    } catch (e) {
      onError(e.toString());
      AICOLog.error('Failed to start streaming', 
        topic: 'message_repository/streaming_start_error',
        error: e,
        extra: {'message_id': message.id});
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
