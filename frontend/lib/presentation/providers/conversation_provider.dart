import 'dart:async';

import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/data/repositories/message_repository_impl.dart';
import 'package:aico_frontend/domain/entities/message.dart';
import 'package:aico_frontend/domain/repositories/message_repository.dart';
import 'package:aico_frontend/domain/usecases/send_message_usecase.dart';
import 'package:aico_frontend/presentation/providers/auth_provider.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:uuid/uuid.dart';

part 'conversation_provider.g.dart';

/// Represents a single thinking turn/step in the conversation
/// This is a data model, not UI state
class ThinkingTurn {
  final String content;
  final DateTime timestamp;
  final String messageId; // Which message this thinking belongs to
  final bool isComplete;

  const ThinkingTurn({
    required this.content,
    required this.timestamp,
    required this.messageId,
    this.isComplete = true,
  });

  ThinkingTurn copyWith({
    String? content,
    DateTime? timestamp,
    String? messageId,
    bool? isComplete,
  }) {
    return ThinkingTurn(
      content: content ?? this.content,
      timestamp: timestamp ?? this.timestamp,
      messageId: messageId ?? this.messageId,
      isComplete: isComplete ?? this.isComplete,
    );
  }
}

/// State class for conversation management
/// Following AICO guidelines: Clear separation of data state from UI state
class ConversationState {
  final List<Message> messages;
  final bool isLoading;
  final bool isSendingMessage;
  final bool isStreaming;
  final String? streamingContent;
  final String? streamingMessageId;
  final String? streamingThinking; // Current thinking being streamed
  final List<ThinkingTurn> thinkingHistory; // Complete history of thinking turns
  final String? error;
  final String? currentConversationId;

  const ConversationState({
    this.messages = const [],
    this.isLoading = false,
    this.isSendingMessage = false,
    this.isStreaming = false,
    this.streamingContent,
    this.streamingMessageId,
    this.streamingThinking,
    this.thinkingHistory = const [],
    this.error,
    this.currentConversationId,
  });

  ConversationState copyWith({
    List<Message>? messages,
    bool? isLoading,
    bool? isSendingMessage,
    bool? isStreaming,
    String? streamingContent,
    String? streamingMessageId,
    String? streamingThinking,
    List<ThinkingTurn>? thinkingHistory,
    String? error,
    String? currentConversationId,
  }) {
    return ConversationState(
      messages: messages ?? this.messages,
      isLoading: isLoading ?? this.isLoading,
      isSendingMessage: isSendingMessage ?? this.isSendingMessage,
      isStreaming: isStreaming ?? this.isStreaming,
      streamingContent: streamingContent ?? this.streamingContent,
      streamingMessageId: streamingMessageId ?? this.streamingMessageId,
      streamingThinking: streamingThinking ?? this.streamingThinking,
      thinkingHistory: thinkingHistory ?? this.thinkingHistory,
      error: error ?? this.error,
      currentConversationId: currentConversationId ?? this.currentConversationId,
    );
  }

  ConversationState clearError() {
    return copyWith(error: null);
  }
}

/// Conversation provider using Riverpod Notifier
@riverpod
class ConversationNotifier extends _$ConversationNotifier {
  late final MessageRepository _messageRepository;
  late final SendMessageUseCase _sendMessageUseCase;
  late final String _userId;
  static const _uuid = Uuid();

  @override
  ConversationState build() {
    // Initialize dependencies from ref
    _messageRepository = ref.read(messageRepositoryProvider);
    _sendMessageUseCase = ref.read(sendMessageUseCaseProvider);
    
    // Get current user ID from auth provider
    final authState = ref.read(authProvider);
    _userId = authState.user?.id ?? 'anonymous';
    
    _initializeConversation();
    return const ConversationState();
  }

  void _initializeConversation() {
    AICOLog.info('Initializing conversation provider', 
      topic: 'conversation_provider/init',
      extra: {'user_id': _userId});
    
    // Initial state already has null conversation ID - backend will assign one for the first message
    // No need to mutate state here as it causes circular dependency
  }


  /// Send message with optional streaming response
  Future<void> sendMessage(String content, {bool stream = false}) async {
    if (content.trim().isEmpty) {
      AICOLog.warn('Attempted to send empty message', 
        topic: 'conversation_provider/send_empty');
      return;
    }

    final messageId = _uuid.v4();
    final timestamp = DateTime.now().toUtc();

    // Create user message
    final userMessage = Message(
      id: messageId,
      content: content.trim(),
      userId: _userId,
      conversationId: state.currentConversationId ?? 'default', // Backend will assign if null
      type: MessageType.text,
      status: MessageStatus.sending,
      timestamp: timestamp,
    );

    // Add user message to state immediately (optimistic update)
    state = state.copyWith(
      messages: [...state.messages, userMessage],
      isSendingMessage: true,
      error: null,
    );

    AICOLog.info('Sending message', 
      topic: 'conversation_provider/send_message',
      extra: {
        'message_id': messageId,
        'conversation_id': state.currentConversationId,
        'streaming': stream,
      });

    try {
      if (stream) {
        // Always use streaming when requested - backend will handle conversation_id creation
        await _handleStreamingMessage(userMessage, messageId);
      } else {
        // Non-streaming path (when explicitly requested)
        await _handleNonStreamingMessage(userMessage, messageId);
      }
    } catch (e) {
      AICOLog.error('Failed to send message', 
        topic: 'conversation_provider/send_error',
        error: e,
        extra: {'message_id': messageId});

      // Update user message status to failed
      final updatedMessages = state.messages.map((msg) {
        if (msg.id == messageId) {
          return msg.copyWith(status: MessageStatus.failed);
        }
        return msg;
      }).toList();

      state = state.copyWith(
        messages: updatedMessages,
        isSendingMessage: false,
        isStreaming: false,
        streamingContent: null,
        streamingMessageId: null,
        error: 'Failed to send message: ${e.toString()}',
      );
    }
  }

  /// Handle streaming message flow
  Future<void> _handleStreamingMessage(Message userMessage, String messageId) async {
    // Create AI message placeholder for streaming
    final aiMessageId = _uuid.v4();
    final aiMessage = Message(
      id: aiMessageId,
      content: '', // Start with empty content
      userId: 'aico',
      conversationId: userMessage.conversationId,
      type: MessageType.text,
      status: MessageStatus.sending,
      timestamp: DateTime.now().toUtc(),
    );

    // Add AI message placeholder and start streaming
    // CRITICAL: Reset both streamingContent AND streamingThinking for new turn
    state = state.copyWith(
      messages: [...state.messages, aiMessage],
      isSendingMessage: false,
      isStreaming: true,
      streamingMessageId: aiMessageId,
      streamingContent: '',
      streamingThinking: '', // Reset thinking for new conversation turn
    );

    // Update user message to sent
    final updatedMessages = state.messages.map((msg) {
      if (msg.id == messageId) {
        return msg.copyWith(status: MessageStatus.sent);
      }
      return msg;
    }).toList();

    state = state.copyWith(messages: updatedMessages);

    // Start streaming via repository
    final repo = _messageRepository as MessageRepositoryImpl;
    
    await repo.sendMessageStreaming(
      userMessage,
      (String chunk, {String? contentType}) {
        // Route chunks by content_type: "thinking" or "response"
        if (contentType == 'thinking') {
          // Update thinking content (displayed in right drawer)
          final currentThinking = state.streamingThinking ?? '';
          final newThinking = currentThinking + chunk;
          state = state.copyWith(streamingThinking: newThinking);
        } else {
          // Update response content (displayed in chat bubble)
          final currentContent = state.streamingContent ?? '';
          final newContent = currentContent + chunk;
          
          state = state.copyWith(streamingContent: newContent);
          
          // Update the AI message in the list
          final updatedMessages = state.messages.map((msg) {
            if (msg.id == aiMessageId) {
              return msg.copyWith(content: newContent);
            }
            return msg;
          }).toList();
          
          state = state.copyWith(messages: updatedMessages);
        }
      },
      (String finalResponse, {String? thinking}) {
        // Finalize the AI message with thinking
        final updatedMessages = state.messages.map((msg) {
          if (msg.id == aiMessageId) {
            return msg.copyWith(
              content: finalResponse,
              thinking: thinking, // Store thinking in message
              status: MessageStatus.sent,
            );
          }
          return msg;
        }).toList();
        
        // Finalize thinking turn and add to history
        // Following AICO guidelines: Single source of truth for data state
        List<ThinkingTurn> updatedHistory = state.thinkingHistory;
        if (state.streamingThinking != null && state.streamingThinking!.trim().isNotEmpty) {
          updatedHistory = [
            ...state.thinkingHistory,
            ThinkingTurn(
              content: state.streamingThinking!.trim(),
              timestamp: DateTime.now(),
              messageId: aiMessageId,
              isComplete: true,
            ),
          ];
        }
        
        state = state.copyWith(
          messages: updatedMessages,
          isStreaming: false,
          streamingContent: null,
          streamingMessageId: null,
          streamingThinking: null, // Clear streaming thinking
          thinkingHistory: updatedHistory, // Update history
        );
        
        AICOLog.info('Streaming completed successfully', 
          topic: 'conversation_provider/streaming_complete',
          extra: {
            'ai_message_id': aiMessageId,
            'final_length': finalResponse.length,
          });
      },
      (String error) {
        // Handle streaming error
        final updatedMessages = state.messages.map((msg) {
          if (msg.id == aiMessageId) {
            return msg.copyWith(
              content: 'Error: $error',
              status: MessageStatus.failed,
            );
          }
          return msg;
        }).toList();
        
        state = state.copyWith(
          messages: updatedMessages,
          isStreaming: false,
          streamingContent: null,
          streamingMessageId: null,
          streamingThinking: null, // Clear thinking on error
          error: 'Streaming failed: $error',
        );
        
        AICOLog.error('Streaming failed', 
          topic: 'conversation_provider/streaming_error',
          error: error,
          extra: {'ai_message_id': aiMessageId});
      },
      onConversationId: (String conversationId) {
        // Update conversation ID from backend
        state = state.copyWith(currentConversationId: conversationId);
        AICOLog.info('Updated conversation_id from backend',
          topic: 'conversation_provider/conversation_id_updated',
          extra: {'conversation_id': conversationId});
      },
    );
  }

  /// Handle non-streaming message flow (existing logic)
  Future<void> _handleNonStreamingMessage(Message userMessage, String messageId) async {
    // Use existing use case for non-streaming
    final params = SendMessageParams(
      content: userMessage.content,
      userId: _userId,
      conversationId: state.currentConversationId ?? 'default',
      type: MessageType.text,
    );

    final sentMessage = await _sendMessageUseCase.call(params);

    // Update user message status to "sent"
    final updatedMessages = state.messages.map((msg) {
      if (msg.id == messageId) {
        return msg.copyWith(
          status: MessageStatus.sent,
          conversationId: sentMessage.conversationId,
        );
      }
      return msg;
    }).toList();

    // Update conversation ID if backend resolved to a different one
    final newConversationId = sentMessage.conversationId != state.currentConversationId 
        ? sentMessage.conversationId 
        : state.currentConversationId;

    state = state.copyWith(
      messages: updatedMessages,
      isSendingMessage: false,
      currentConversationId: newConversationId,
    );

    // Handle AI response from backend using the backend response data
    await _handleAIResponse(sentMessage);
  }

  /// Handle AI response from backend
  Future<void> _handleAIResponse(Message userMessage) async {
    try {
      // Extract AI response from user message metadata (set by repository)
      final aiResponseContent = userMessage.metadata?['ai_response'] as String?;
      
      if (aiResponseContent != null && aiResponseContent.isNotEmpty) {
        // Debug: Print the backend timestamp to see what we're actually getting
        final backendTimestamp = userMessage.metadata?['backend_timestamp'] as String?;
        debugPrint('Backend timestamp debug: $backendTimestamp, Current time: ${DateTime.now().toIso8601String()}');
        
        // For now, use current time to eliminate the 2-hour offset
        final aiTimestamp = DateTime.now();
        
        final aiMessage = Message(
          id: _uuid.v4(),
          content: aiResponseContent,
          userId: 'aico', // Special user ID for AICO
          conversationId: userMessage.conversationId,
          type: MessageType.text,
          status: MessageStatus.sent,
          timestamp: aiTimestamp,
        );

        state = state.copyWith(
          messages: [...state.messages, aiMessage],
        );

        AICOLog.info('AI response added from backend', 
          topic: 'conversation_provider/ai_response',
          extra: {
            'ai_message_id': aiMessage.id,
            'conversation_id': aiMessage.conversationId,
            'content_length': aiResponseContent.length,
          });
      } else {
        AICOLog.warn('No AI response received from backend', 
          topic: 'conversation_provider/ai_response_missing',
          extra: {
            'user_message_id': userMessage.id,
            'conversation_id': userMessage.conversationId,
          });
      }

    } catch (e) {
      AICOLog.error('Failed to handle AI response', 
        topic: 'conversation_provider/ai_response_error',
        error: e,
        extra: {'user_message_id': userMessage.id});
    }
  }

  /// Load conversation history
  Future<void> loadMessages({String? conversationId}) async {
    final targetConversationId = conversationId ?? state.currentConversationId ?? 'default';
    
    state = state.copyWith(isLoading: true, error: null);

    AICOLog.info('Loading conversation messages', 
      topic: 'conversation_provider/load_messages',
      extra: {'conversation_id': targetConversationId});

    try {
      final messages = await _messageRepository.getMessages(targetConversationId);
      
      state = state.copyWith(
        messages: messages,
        isLoading: false,
        currentConversationId: targetConversationId,
      );

      AICOLog.info('Messages loaded successfully', 
        topic: 'conversation_provider/load_success',
        extra: {
          'conversation_id': targetConversationId,
          'message_count': messages.length,
        });

    } catch (e) {
      AICOLog.error('Failed to load messages', 
        topic: 'conversation_provider/load_error',
        error: e,
        extra: {'conversation_id': targetConversationId});

      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load messages: ${e.toString()}',
      );
    }
  }

  /// Clear current conversation
  void clearConversation() {
    AICOLog.info('Clearing conversation', 
      topic: 'conversation_provider/clear');
    
    state = const ConversationState(currentConversationId: null);
  }

  /// Clear error state
  void clearError() {
    state = state.clearError();
  }

  /// Retry failed message
  Future<void> retryMessage(String messageId) async {
    final message = state.messages.firstWhere(
      (msg) => msg.id == messageId,
      orElse: () => throw ArgumentError('Message not found: $messageId'),
    );

    if (message.status != MessageStatus.failed) {
      AICOLog.warn('Attempted to retry non-failed message', 
        topic: 'conversation_provider/retry_invalid',
        extra: {
          'message_id': messageId,
          'status': message.status.name,
        });
      return;
    }

    AICOLog.info('Retrying failed message', 
      topic: 'conversation_provider/retry',
      extra: {'message_id': messageId});

    // Remove the failed message and resend
    final updatedMessages = state.messages.where((msg) => msg.id != messageId).toList();
    state = state.copyWith(messages: updatedMessages);

    await sendMessage(message.content);
  }
}

/// Provider for message repository
@riverpod
MessageRepository messageRepository(Ref ref) {
  final apiClient = ref.read(unifiedApiClientProvider);
  return MessageRepositoryImpl(apiClient);
}

/// Provider for send message use case
@riverpod
SendMessageUseCase sendMessageUseCase(Ref ref) {
  final messageRepository = ref.read(messageRepositoryProvider);
  return SendMessageUseCase(messageRepository);
}
