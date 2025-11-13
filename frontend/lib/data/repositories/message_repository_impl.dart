import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/data/models/message_model.dart';
import 'package:aico_frontend/domain/entities/message.dart';
import 'package:aico_frontend/domain/repositories/message_repository.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';
import 'package:aico_frontend/data/database/message_database.dart' hide Message;
import 'package:drift/drift.dart';

/// Implementation of MessageRepository with local persistence
class MessageRepositoryImpl implements MessageRepository {
  final UnifiedApiClient _apiClient;
  final MessageDatabase _database;

  const MessageRepositoryImpl(this._apiClient, this._database);

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
        final serverMessageId = response['message_id'] as String;
        final conversationId = response['conversation_id'] as String;
        final aiResponse = response['ai_response'] as String?;
        
        // Store both messages atomically in local database
        if (aiResponse != null && aiResponse.isNotEmpty) {
          final timestamp = DateTime.parse(response['timestamp'] as String);
          
          await _database.insertConversationPair(
            MessagesCompanion.insert(
              id: serverMessageId,
              conversationId: conversationId,
              userId: message.userId,
              content: message.content,
              role: 'user',
              timestamp: timestamp,
              messageType: const Value('text'),
              status: const Value('sent'),
              syncedAt: Value(DateTime.now()),
              needsSync: const Value(false),
            ),
            MessagesCompanion.insert(
              id: '${serverMessageId}_ai',
              conversationId: conversationId,
              userId: 'aico',
              content: aiResponse,
              role: 'assistant',
              timestamp: DateTime.now(),
              messageType: const Value('text'),
              status: const Value('received'),
              syncedAt: Value(DateTime.now()),
              needsSync: const Value(false),
            ),
          );
        }
        
        final sentMessage = Message(
          id: serverMessageId,
          content: message.content,
          userId: message.userId,
          conversationId: conversationId,
          type: message.type,
          status: MessageStatus.sent,
          timestamp: message.timestamp,
          metadata: {
            'conversation_action': response['conversation_action'] as String,
            'conversation_reasoning': response['conversation_reasoning'] as String,
            'backend_status': response['status'] as String,
            'ai_response': aiResponse,
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
            if (chunkData.containsKey('message_id')) {
              backendMessageId = chunkData['message_id'] as String?;
              
              // Notify caller of backend message_id
              if (backendMessageId != null && onMessageId != null) {
                onMessageId(backendMessageId!);
              }
            }
          }

          if (contentType == 'thinking') {
            accumulatedThinking += chunk;
          } else {
            accumulatedContent += chunk;
          }

          onChunk(chunk, contentType: contentType);
        },
        onComplete: () async {
          if (backendConversationId != null && onConversationId != null) {
            onConversationId(backendConversationId!);
          }
          
          // Update message ID if backend provided one
          if (backendMessageId != null) {
            message = message.copyWith(id: backendMessageId!);
          }

          // Cache both user message and AI response
          final conversationId = backendConversationId ?? message.conversationId;
          final messageId = backendMessageId ?? message.id;
          
          try {
            debugPrint('💾 [Streaming Cache] Storing pair - User: "${message.content.substring(0, 20)}..." AI: "${accumulatedContent.substring(0, 20)}..."');
            debugPrint('💾 [Streaming Cache] User userId=${message.userId}, AI userId=aico');
            
            await _database.insertConversationPair(
              // User message FIRST
              MessagesCompanion.insert(
                id: messageId,
                conversationId: conversationId,
                userId: message.userId, // User's UUID
                content: message.content, // User's message
                role: 'user',
                timestamp: message.timestamp,
                messageType: const Value('text'),
                status: const Value('sent'),
                syncedAt: Value(DateTime.now()),
                needsSync: const Value(false),
              ),
              // AI response SECOND
              MessagesCompanion.insert(
                id: '${messageId}_ai',
                conversationId: conversationId,
                userId: 'aico', // AI userId
                content: accumulatedContent, // AI response
                role: 'assistant',
                timestamp: DateTime.now(),
                messageType: const Value('text'),
                status: const Value('received'),
                syncedAt: Value(DateTime.now()),
                needsSync: const Value(false),
              ),
            );
            
            debugPrint('✅ [Streaming Cache] Successfully cached conversation pair');
            AICOLog.info('Cached streaming conversation pair',
              topic: 'message_repository/cache_streaming',
              extra: {
                'conversation_id': conversationId,
                'message_id': messageId,
                'response_length': accumulatedContent.length,
              });
          } catch (e) {
            debugPrint('❌ [Streaming Cache] FAILED: $e');
            AICOLog.error('Failed to cache streaming messages',
              topic: 'message_repository/cache_streaming_error',
              error: e);
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

  /// Get messages for a conversation (cache-first pattern)
  @override
  Future<List<Message>> getMessages(
    String conversationId, {
    int? limit,
    String? beforeMessageId,
    Function(List<Message>)? onBackgroundSyncComplete,
  }) async {
    try {
      // 1. Load from local cache first (instant)
      final cachedMessages = await _database.getConversationMessages(conversationId);
      
      if (cachedMessages.isNotEmpty) {
        debugPrint('📥 [Cache] Raw DB query returned ${cachedMessages.length} messages for conversation: $conversationId');
        debugPrint('📥 [Cache] NEWEST message (first): ${cachedMessages.first.timestamp} - "${cachedMessages.first.content.substring(0, 30)}..."');
        debugPrint('📥 [Cache] OLDEST message (last): ${cachedMessages.last.timestamp} - "${cachedMessages.last.content.substring(0, 30)}..."');
        
        // 2. Return cached data immediately (reverse since DB returns DESC)
        final messages = cachedMessages.map((dbMsg) {
          final preview = dbMsg.content.length > 30 ? dbMsg.content.substring(0, 30) : dbMsg.content;
          debugPrint('💾 [Cache] ${dbMsg.timestamp.toIso8601String()} | userId=${dbMsg.userId} | role=${dbMsg.role} | $preview...');
          return Message(
            id: dbMsg.id,
            content: dbMsg.content,
            userId: dbMsg.userId,
            conversationId: dbMsg.conversationId,
            type: MessageType.text,
            status: MessageStatus.sent,
            timestamp: dbMsg.timestamp,
          );
        }).toList().reversed.toList(); // Reverse to get oldest-first for chat UI
        
        debugPrint('📊 [Cache] After reverse - First: ${messages.first.timestamp}, Last: ${messages.last.timestamp}');
        debugPrint('📊 [Cache] Returning ${messages.length} messages (limit: 50)');
        
        // 3. Sync in background (fire and forget)
        _syncMessagesInBackground(conversationId, onComplete: onBackgroundSyncComplete);
        
        return messages;
      }
      
      // 4. Cache empty - fetch from backend
      return await _fetchMessagesFromBackend(conversationId, limit: limit, beforeMessageId: beforeMessageId);
      
    } catch (e) {
      AICOLog.error('Failed to get messages', 
        topic: 'message_repository/get_messages_error',
        error: e,
        extra: {'conversation_id': conversationId});
      
      return [];
    }
  }

  Future<List<Message>> _fetchMessagesFromBackend(String conversationId, {int? limit, String? beforeMessageId}) async {
    final queryParams = <String, String>{
      'page': '1',
      if (limit != null) 'page_size': limit.toString(),
      if (beforeMessageId != null) 'before': beforeMessageId,
    };

    final response = await _apiClient.request<Map<String, dynamic>>(
      'GET',
      '/conversation/messages',
      queryParameters: queryParams,
    );

    if (response != null) {
      final messagesData = response['messages'] as List<dynamic>? ?? [];
      
      debugPrint('🌐 [Backend] Received ${messagesData.length} messages from backend');
      if (messagesData.isNotEmpty) {
        debugPrint('🌐 [Backend] NEWEST message: ${messagesData.first}');
        debugPrint('🌐 [Backend] OLDEST message: ${messagesData.last}');
      }
      
      final messages = messagesData
          .map((json) => MessageModel.fromJson(json as Map<String, dynamic>))
          .map((model) => model.toEntity())
          .toList()
          .reversed.toList(); // Backend returns DESC, reverse to ASC for chat UI

      // Store in cache for next time
      // Note: MessageModel.fromJson already converted userId to 'aico' for assistant messages
      for (final msg in messages) {
        final role = msg.userId == 'aico' ? 'assistant' : 'user';
        
        debugPrint('💾 [Backend Cache] ${msg.id.substring(0, 8)}... userId=${msg.userId}, role=$role');
        
        await _database.into(_database.messages).insertOnConflictUpdate(
          MessagesCompanion.insert(
            id: msg.id,
            conversationId: msg.conversationId,
            userId: msg.userId,
            content: msg.content,
            role: role,
            timestamp: msg.timestamp,
            syncedAt: Value(DateTime.now()),
          ),
        );
      }

      return messages;
    } else {
      throw Exception('Failed to fetch messages: null response');
    }
  }

  void _syncMessagesInBackground(String conversationId, {Function(List<Message>)? onComplete}) {
    _fetchMessagesFromBackend(conversationId).then((messages) {
      AICOLog.info('Background sync completed', 
        topic: 'message_repository/background_sync',
        extra: {'conversation_id': conversationId, 'count': messages.length});
      
      // Notify caller with fresh messages
      if (onComplete != null) {
        onComplete(messages);
      }
    }).catchError((e) {
      AICOLog.warn('Background sync failed', 
        topic: 'message_repository/background_sync_error',
        error: e);
    });
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
