import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../models/conversation_message.dart';
import '../../../providers/conversation_provider.dart';
import '../../../theme/glassmorphism.dart';
import '../../../widgets/chat/interactive_message_bubble.dart';
import 'home_toolbar.dart';

/// Conversation area displaying messages or welcome state
/// 
/// Handles:
/// - Welcome message with fade animation
/// - Message list with auto-scroll
/// - Error states
/// - Conversation toolbar
class HomeConversationArea extends ConsumerStatefulWidget {
  final ScrollController scrollController;
  final Color accentColor;
  final AnimationController glowController;
  final Animation<double> glowAnimation;
  final void Function(String messageId, bool isPositive)? onFeedback;
  final VoidCallback onCopy;
  final VoidCallback onSave;
  final VoidCallback? onRemember;

  const HomeConversationArea({
    super.key,
    required this.scrollController,
    required this.accentColor,
    required this.glowController,
    required this.glowAnimation,
    this.onFeedback,
    required this.onCopy,
    required this.onSave,
    this.onRemember,
  });

  @override
  ConsumerState<HomeConversationArea> createState() => _HomeConversationAreaState();
}

class _HomeConversationAreaState extends ConsumerState<HomeConversationArea> {
  bool _showConversationActions = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final conversationState = ref.watch(conversationProvider);
    final hasMessages = conversationState.messages.isNotEmpty;

    // Error state
    if (conversationState.error != null) {
      return _buildErrorState(context, theme, conversationState.error!);
    }

    // Welcome state (no messages)
    if (conversationState.messages.isEmpty) {
      return _buildWelcomeState(context, theme, conversationState.isLoading);
    }

    // Messages state
    return MouseRegion(
      onEnter: hasMessages ? (_) => setState(() => _showConversationActions = true) : null,
      onExit: hasMessages ? (_) => setState(() => _showConversationActions = false) : null,
      child: Column(
        children: [
          Expanded(
            child: _buildMessageList(context, theme, conversationState),
          ),
          // Conversation toolbar
          HomeToolbar(
            isVisible: _showConversationActions,
            hasMessages: hasMessages,
            accentColor: widget.accentColor,
            onCopy: widget.onCopy,
            onSave: widget.onSave,
            onRemember: widget.onRemember,
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState(BuildContext context, ThemeData theme, String error) {
    final isDark = theme.brightness == Brightness.dark;
    
    return Center(
      child: Container(
        padding: const EdgeInsets.all(32),
        margin: const EdgeInsets.all(40),
        decoration: GlassTheme.glassCard(
          isDark: isDark,
          radius: GlassTheme.radiusLarge,
          accentColor: theme.colorScheme.error,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: theme.colorScheme.error.withValues(alpha: 0.1),
              ),
              child: Icon(
                Icons.error_outline_rounded,
                size: 48,
                color: theme.colorScheme.error,
              ),
            ),
            const SizedBox(height: 20),
            Text(
              'Error loading conversation',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              error,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildWelcomeState(BuildContext context, ThemeData theme, bool isLoading) {
    return Center(
      child: TweenAnimationBuilder<double>(
        tween: Tween(begin: 0.0, end: isLoading ? 0.5 : 1.0),
        duration: const Duration(milliseconds: 800),
        curve: Curves.easeInOut,
        builder: (context, opacity, child) {
          return AnimatedBuilder(
            animation: widget.glowController,
            builder: (context, child) {
              // Gentle fade-in only (no jitter, no scale)
              final fadeOpacity = opacity * (0.85 + (widget.glowAnimation.value * 0.15));
              
              return Opacity(
                opacity: fadeOpacity,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 48),
                  child: Text(
                    'I\'m here',
                    style: theme.textTheme.displaySmall?.copyWith(
                      fontWeight: FontWeight.w200,
                      letterSpacing: -0.3,
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.9),
                      height: 1.2,
                    ),
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }

  Widget _buildMessageList(BuildContext context, ThemeData theme, ConversationState conversationState) {
    return ShaderMask(
      shaderCallback: (Rect bounds) {
        return const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.transparent,
            Colors.black,
            Colors.black,
            Colors.transparent,
          ],
          stops: [0.0, 0.15, 0.85, 1.0],
        ).createShader(bounds);
      },
      blendMode: BlendMode.dstIn,
      child: ScrollConfiguration(
        behavior: ScrollConfiguration.of(context).copyWith(scrollbars: false),
        child: Scrollbar(
          controller: widget.scrollController,
          thumbVisibility: true,
          child: TweenAnimationBuilder<double>(
            tween: Tween(begin: 0.0, end: conversationState.isLoading ? 0.0 : 1.0),
            duration: const Duration(milliseconds: 1200),
            curve: Curves.easeInOutCubic,
            builder: (context, opacity, child) {
              return Opacity(
                opacity: opacity,
                child: child,
              );
            },
            child: ListView.builder(
              controller: widget.scrollController,
              reverse: true, // Bottom-to-top scroll for chat
              padding: const EdgeInsets.all(24),
              itemCount: conversationState.messages.length,
              itemBuilder: (context, index) {
                // Reverse index since list is reversed
                final reversedIndex = conversationState.messages.length - 1 - index;
                final message = conversationState.messages[reversedIndex];
                
                return _buildMessageBubble(context, theme, message, conversationState);
              },
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMessageBubble(
    BuildContext context,
    ThemeData theme,
    message,
    ConversationState conversationState,
  ) {
    // Convert domain Message to presentation ConversationMessage
    final conversationMessage = ConversationMessage(
      id: message.id,
      isFromAico: message.userId == 'aico',
      message: message.content,
      timestamp: message.timestamp,
    );
    
    // Check if this is the last message and AICO is currently thinking/processing
    final isLastMessage = conversationState.messages.isNotEmpty && 
                          conversationState.messages.last.timestamp == message.timestamp;
    
    // Show thinking particles when:
    // 1. Message is being sent (isSendingMessage)
    // 2. OR thinking content is streaming but response hasn't started yet
    final hasThinkingContent = conversationState.streamingThinking != null && 
                               conversationState.streamingThinking!.isNotEmpty;
    final responseHasStarted = conversationMessage.message.isNotEmpty;
    
    final isStreamingOrProcessing = conversationState.isSendingMessage || 
                                    (hasThinkingContent && !responseHasStarted);
    
    final isThinking = conversationMessage.isFromAico && 
                       isLastMessage && 
                       isStreamingOrProcessing;
    
    return InteractiveMessageBubble(
      content: conversationMessage.message,
      isFromAico: conversationMessage.isFromAico,
      isThinking: isThinking,
      timestamp: conversationMessage.timestamp,
      accentColor: widget.accentColor,
      messageId: conversationMessage.id,
      conversationId: conversationState.currentConversationId,
      onFeedback: conversationMessage.isFromAico && conversationMessage.id != null && widget.onFeedback != null
          ? (isPositive) => widget.onFeedback!(conversationMessage.id!, isPositive)
          : null,
    );
  }
}
