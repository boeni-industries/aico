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
import 'package:uuid/uuid.dart';

/// State class for conversation management
class ConversationState {
  final List<Message> messages;
  final bool isLoading;
  final bool isSendingMessage;
  final String? error;
  final String? currentThreadId;

  const ConversationState({
    this.messages = const [],
    this.isLoading = false,
    this.isSendingMessage = false,
    this.error,
    this.currentThreadId,
  });

  ConversationState copyWith({
    List<Message>? messages,
    bool? isLoading,
    bool? isSendingMessage,
    String? error,
    String? currentThreadId,
  }) {
    return ConversationState(
      messages: messages ?? this.messages,
      isLoading: isLoading ?? this.isLoading,
      isSendingMessage: isSendingMessage ?? this.isSendingMessage,
      error: error ?? this.error,
      currentThreadId: currentThreadId ?? this.currentThreadId,
    );
  }

  ConversationState clearError() {
    return copyWith(error: null);
  }
}

/// Conversation provider using Riverpod StateNotifier
class ConversationNotifier extends StateNotifier<ConversationState> {
  final MessageRepository _messageRepository;
  final SendMessageUseCase _sendMessageUseCase;
  final String _userId;
  static const _uuid = Uuid();

  ConversationNotifier(
    this._messageRepository,
    this._sendMessageUseCase,
    this._userId,
  ) : super(const ConversationState()) {
    _initializeConversation();
  }


  void _initializeConversation() {
    AICOLog.info('Initializing conversation provider', 
      topic: 'conversation_provider/init',
      extra: {'user_id': _userId});
    
    // Start with a default thread ID - backend will handle thread resolution
    state = state.copyWith(currentThreadId: 'default');
  }

  /// Send a message to AICO
  Future<void> sendMessage(String content) async {
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
      conversationId: state.currentThreadId ?? 'default',
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
        'content_length': content.length,
        'thread_id': state.currentThreadId,
      });

    try {
      // Send message through use case with timeout to prevent UI freeze
      final params = SendMessageParams(
        content: content.trim(),
        userId: _userId,
        conversationId: state.currentThreadId ?? 'default',
        type: MessageType.text,
      );

      final sentMessage = await _sendMessageUseCase.call(params);

      // Only update user message status to "sent" - don't overwrite the entire message
      final updatedMessages = state.messages.map((msg) {
        if (msg.id == messageId) {
          return msg.copyWith(
            status: MessageStatus.sent,
            conversationId: sentMessage.conversationId, // Update thread ID if changed
          );
        }
        return msg;
      }).toList();

      // Update thread ID if backend resolved to a different one
      final newThreadId = sentMessage.conversationId != state.currentThreadId 
          ? sentMessage.conversationId 
          : state.currentThreadId;

      state = state.copyWith(
        messages: updatedMessages,
        isSendingMessage: false,
        currentThreadId: newThreadId,
      );

      AICOLog.info('Message sent successfully', 
        topic: 'conversation_provider/send_success',
        extra: {
          'message_id': sentMessage.id,
          'thread_id': sentMessage.conversationId,
        });

      // Handle AI response from backend using the backend response data
      await _handleAIResponse(sentMessage);

    } catch (e) {
      AICOLog.error('Failed to send message', 
        topic: 'conversation_provider/send_error',
        error: e,
        extra: {'message_id': messageId});

      // Update message status to failed
      final updatedMessages = state.messages.map((msg) {
        if (msg.id == messageId) {
          return msg.copyWith(status: MessageStatus.failed);
        }
        return msg;
      }).toList();

      state = state.copyWith(
        messages: updatedMessages,
        isSendingMessage: false,
        error: 'Failed to send message: ${e.toString()}',
      );
    }
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
            'thread_id': aiMessage.conversationId,
            'content_length': aiResponseContent.length,
          });
      } else {
        AICOLog.warn('No AI response received from backend', 
          topic: 'conversation_provider/ai_response_missing',
          extra: {
            'user_message_id': userMessage.id,
            'thread_id': userMessage.conversationId,
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
  Future<void> loadMessages({String? threadId}) async {
    final targetThreadId = threadId ?? state.currentThreadId ?? 'default';
    
    state = state.copyWith(isLoading: true, error: null);

    AICOLog.info('Loading conversation messages', 
      topic: 'conversation_provider/load_messages',
      extra: {'thread_id': targetThreadId});

    try {
      final messages = await _messageRepository.getMessages(targetThreadId);
      
      state = state.copyWith(
        messages: messages,
        isLoading: false,
        currentThreadId: targetThreadId,
      );

      AICOLog.info('Messages loaded successfully', 
        topic: 'conversation_provider/load_success',
        extra: {
          'thread_id': targetThreadId,
          'message_count': messages.length,
        });

    } catch (e) {
      AICOLog.error('Failed to load messages', 
        topic: 'conversation_provider/load_error',
        error: e,
        extra: {'thread_id': targetThreadId});

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
    
    state = const ConversationState(currentThreadId: 'default');
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

/// Provider for conversation state management
final conversationProvider = StateNotifierProvider<ConversationNotifier, ConversationState>((ref) {
  final messageRepository = ref.read(messageRepositoryProvider);
  final sendMessageUseCase = ref.read(sendMessageUseCaseProvider);
  
  // Get current user ID from auth provider
  final authState = ref.read(authProvider);
  final userId = authState.user?.id ?? 'anonymous';

  return ConversationNotifier(
    messageRepository,
    sendMessageUseCase,
    userId,
  );
});

/// Provider for message repository
final messageRepositoryProvider = Provider<MessageRepository>((ref) {
  final apiClient = ref.read(unifiedApiClientProvider);
  return MessageRepositoryImpl(apiClient);
});

/// Provider for send message use case
final sendMessageUseCaseProvider = Provider<SendMessageUseCase>((ref) {
  final messageRepository = ref.read(messageRepositoryProvider);
  return SendMessageUseCase(messageRepository);
});
