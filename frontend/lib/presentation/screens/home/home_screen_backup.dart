import 'dart:async';
import 'dart:ui';

import 'package:aico_frontend/presentation/models/conversation_message.dart';
import 'package:aico_frontend/presentation/providers/avatar_state_provider.dart';
import 'package:aico_frontend/presentation/providers/conversation_provider.dart';
import 'package:aico_frontend/presentation/providers/memory_album_provider.dart';
import 'package:aico_frontend/presentation/screens/admin/admin_screen.dart';
import 'package:aico_frontend/presentation/screens/home/handlers/conversation_export_handler.dart';
import 'package:aico_frontend/presentation/screens/home/helpers/home_screen_helpers.dart';
import 'package:aico_frontend/presentation/screens/home/widgets/home_avatar_header.dart';
import 'package:aico_frontend/presentation/screens/home/widgets/home_input_area.dart';
import 'package:aico_frontend/presentation/screens/home/widgets/home_left_drawer.dart';
import 'package:aico_frontend/presentation/screens/home/widgets/home_right_drawer.dart';
import 'package:aico_frontend/presentation/screens/home/widgets/home_toolbar.dart';
import 'package:aico_frontend/presentation/screens/memory/memory_screen.dart';
import 'package:aico_frontend/presentation/screens/settings/settings_screen.dart';
import 'package:aico_frontend/presentation/theme/glassmorphism.dart';
import 'package:aico_frontend/presentation/widgets/chat/interactive_message_bubble.dart';
import 'package:aico_frontend/presentation/widgets/chat/feedback_dialog.dart';
import 'package:aico_frontend/presentation/widgets/common/glassmorphic_toast.dart';
import 'package:aico_frontend/presentation/widgets/conversation/share_conversation_modal.dart';
import 'package:aico_frontend/presentation/providers/behavioral_feedback_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// Export NavigationPage from home_left_drawer to avoid duplication
export 'package:aico_frontend/presentation/screens/home/widgets/home_left_drawer.dart' show NavigationPage;

/// Home screen featuring avatar-centric hub with integrated conversation interface.
/// Serves as the primary interaction point with AICO, including conversation history
/// and collapsible right drawer for thoughts and memory timeline.
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> with TickerProviderStateMixin {
  bool _isRightDrawerOpen = true;
  bool _isRightDrawerExpanded = false; // true = expanded, false = collapsed to icons
  bool _isLeftDrawerExpanded = false; // Start collapsed for more space
  NavigationPage _currentPage = NavigationPage.home;
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _conversationController = ScrollController();
  final FocusNode _messageFocusNode = FocusNode();
  final GlobalKey _sendButtonKey = GlobalKey();
  final GlobalKey _voiceButtonKey = GlobalKey();
  Timer? _typingTimer;
  bool _isUserTyping = false;
  String? _scrollToThoughtId; // Track which thought to scroll to
  Timer? _hoverTimer; // Delay before showing preview
  bool _showConversationActions = false; // Show contextual actions on hover
  
  // Animation controllers for immersive effects
  late AnimationController _backgroundAnimationController;
  late AnimationController _glowAnimationController;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    _messageController.addListener(_onTypingChanged);
    
    // Initialize animation controllers for immersive effects
    _backgroundAnimationController = AnimationController(
      duration: const Duration(seconds: 20),
      vsync: this,
    )..repeat();
    
    _glowAnimationController = AnimationController(
      duration: const Duration(seconds: 3),
      vsync: this,
    )..repeat(reverse: true);
    
    _glowAnimation = Tween<double>(begin: 0.3, end: 0.7).animate(
      CurvedAnimation(parent: _glowAnimationController, curve: Curves.easeInOut),
    );
  }
  
  void _onTypingChanged() {
    final hasText = _messageController.text.trim().isNotEmpty;
    
    // Cancel existing timer
    _typingTimer?.cancel();
    
    if (hasText && !_isUserTyping) {
      // User started typing - switch to listening mode
      setState(() => _isUserTyping = true);
      ref.read(avatarRingStateProvider.notifier).startListening(intensity: 0.6);
    } else if (hasText) {
      // User is still typing - reset timer
      _typingTimer = Timer(const Duration(seconds: 1), () {
        // User stopped typing for 1 second
        if (mounted) {
          setState(() => _isUserTyping = false);
          final avatarNotifier = ref.read(avatarRingStateProvider.notifier);
          final conversationState = ref.read(conversationProvider);
          
          // Return to appropriate state
          if (conversationState.isSendingMessage || conversationState.isStreaming) {
            avatarNotifier.startThinking();
          } else {
            avatarNotifier.returnToIdle();
          }
        }
      });
    } else if (!hasText && _isUserTyping) {
      // Text cleared - return to idle immediately
      setState(() => _isUserTyping = false);
      _typingTimer = Timer(const Duration(seconds: 1), () {
        if (mounted) {
          ref.read(avatarRingStateProvider.notifier).returnToIdle();
        }
      });
    }
  }
  
  @override
  void dispose() {
    _typingTimer?.cancel();
    _hoverTimer?.cancel();
    _messageController.removeListener(_onTypingChanged);
    _messageController.dispose();
    _conversationController.dispose();
    _messageFocusNode.dispose();
    _backgroundAnimationController.dispose();
    _glowAnimationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final avatarState = ref.watch(avatarRingStateProvider);
    
    final accentColor = const Color(0xFFB8A1EA); // Soft purple accent
    final screenWidth = MediaQuery.of(context).size.width;
    final isDesktop = screenWidth > 800;
    
    // Get avatar mood color for atmospheric effect
    final avatarMoodColor = HomeScreenHelpers.getAvatarMoodColor(avatarState.mode, theme.brightness == Brightness.dark);
    
    // Listen for conversation changes to auto-scroll
    ref.listen<ConversationState>(conversationProvider, (previous, next) {
      // Auto-scroll when new messages are added OR when content/thinking changes (streaming)
      bool shouldScroll = false;
      
      if (previous != null) {
        // New message added
        if (next.messages.length > previous.messages.length) {
          shouldScroll = true;
        }
        
        // Message content updated (streaming response)
        else if (next.messages.length == previous.messages.length && next.messages.isNotEmpty) {
          // Check if the last message content has changed (streaming update)
          final lastMessage = next.messages.last;
          final previousLastMessage = previous.messages.isNotEmpty ? previous.messages.last : null;
          
          if (previousLastMessage != null && 
              lastMessage.content != previousLastMessage.content) {
            shouldScroll = true;
          }
        }
        
        // Thinking content updated (streaming inner monologue) - also trigger scroll
        if (next.isStreaming && next.streamingThinking != previous.streamingThinking) {
          shouldScroll = true;
        }
      } else {
        // Initial load from cache - scroll to bottom instantly if messages exist
        if (next.messages.isNotEmpty && !next.isLoading) {
          HomeScreenHelpers.scrollToBottom(_conversationController, instant: true);
          return; // Don't use shouldScroll for initial load
        }
      }
      
      if (shouldScroll) {
        // Don't auto-scroll if user is actively scrolling up (viewing older messages)
        // With reverse: true, position 0 is bottom, higher values are scrolling up
        final isNearBottom = _conversationController.hasClients && 
            _conversationController.position.pixels < 200;
        if (isNearBottom || !_conversationController.hasClients) {
          HomeScreenHelpers.scrollToBottom(_conversationController); // Smooth scroll for new messages
        }
      }
    });
    
    return Scaffold(
        body: AnimatedBuilder(
          animation: _backgroundAnimationController,
          builder: (context, child) {
            return Container(
              // Rich depth gradient - subtle purple/blue tones for glassmorphism
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  center: const Alignment(0, -0.4),
                  radius: 1.2,
                  colors: theme.brightness == Brightness.dark
                      ? [
                          // Rich center - purple-blue for depth
                          const Color(0xFF2D3B5C),
                          // Mid-range - blue-grey transition
                          const Color(0xFF1F2A3E),
                          // Outer - deep blue-grey
                          const Color(0xFF151D2A),
                          // Edges - darkest
                          const Color(0xFF0F1419),
                        ]
                      : [
                          // Light mode: soft purple-blue pastels
                          const Color(0xFFF0F0FF),
                          const Color(0xFFE8ECFA),
                          const Color(0xFFDDE2F0),
                          const Color(0xFFD5DAE8),
                        ],
                  stops: const [0.0, 0.35, 0.7, 1.0],
                ),
              ),
          child: Stack(
          children: [
            // Localized avatar mood glow - subtle atmospheric hint
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              height: 350,
              child: IgnorePointer(
                child: Container(
                  decoration: BoxDecoration(
                    gradient: RadialGradient(
                      center: const Alignment(0, -0.25),
                      radius: 0.5,
                      colors: [
                        avatarMoodColor.withValues(alpha: 0.08),
                        avatarMoodColor.withValues(alpha: 0.04),
                        avatarMoodColor.withValues(alpha: 0.015),
                        Colors.transparent,
                      ],
                      stops: const [0.0, 0.35, 0.65, 1.0],
                    ),
                  ),
                ),
              ),
            ),
            Row(
              children: [
                // Left drawer for navigation - always visible on desktop, toggles between expanded/collapsed
                if (isDesktop)
                  HomeLeftDrawer(
                    accentColor: accentColor,
                    isExpanded: _isLeftDrawerExpanded,
                    currentPage: _currentPage,
                    onToggle: () => setState(() => _isLeftDrawerExpanded = !_isLeftDrawerExpanded),
                    onPageChange: _switchToPage,
                  ),
            
            // Main content area - switches based on selected page
            Expanded(
              flex: (_isRightDrawerOpen && isDesktop) ? 2 : 3,
              child: SafeArea(
                child: _buildMainContent(context, theme, accentColor),
              ),
            ),
            
                // Right drawer for thoughts and memory - always visible on desktop, toggles between expanded/collapsed
                if (_isRightDrawerOpen && isDesktop)
                  HomeRightDrawer(
                    accentColor: accentColor,
                    glowController: _glowAnimationController,
                    glowAnimation: _glowAnimation,
                    isExpanded: _isRightDrawerExpanded,
                    onToggle: () => setState(() => _isRightDrawerExpanded = !_isRightDrawerExpanded),
                    scrollToMessageId: _scrollToThoughtId,
                  ),
              ],
            ),
          ],
        ), // Close Stack
            ); // Close Container
          }, // Close AnimatedBuilder builder
        ), // Close AnimatedBuilder
      floatingActionButton: Stack(
        children: [
        // Floating chevron removed - collapse button now in drawer header
        
        // Show right drawer button when drawer is hidden
        if (isDesktop && !_isRightDrawerOpen)
          Positioned(
            right: 16,
            top: MediaQuery.of(context).size.height / 2 - 24,
            child: Container(
              decoration: BoxDecoration(
                color: theme.colorScheme.surface,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: theme.dividerColor.withValues(alpha: 0.2),
                ),
              ),
              child: IconButton(
                onPressed: () => setState(() => _isRightDrawerOpen = true),
                icon: Icon(
                  Icons.chevron_left,
                  color: accentColor.withValues(alpha: 0.6),
                  size: 20,
                ),
                tooltip: 'Show AICO\'s thoughts',
                style: IconButton.styleFrom(
                  padding: EdgeInsets.zero,
                ),
              ),
            ),
          ),
        ],
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.endTop,
    ); // Close Scaffold
  }

  Widget _buildConversationArea(BuildContext context, ThemeData theme, Color accentColor) {
    final conversationState = ref.watch(conversationProvider);
    final isDark = theme.brightness == Brightness.dark;
    final hasMessages = conversationState.messages.isNotEmpty;
    
    // Removed skeleton loader - just show greeting or messages
    
    if (conversationState.error != null) {
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
                conversationState.error!,
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

    // Smooth fade transition from welcome to messages
    if (conversationState.messages.isEmpty) {
      return Center(
        child: TweenAnimationBuilder<double>(
          tween: Tween(begin: 0.0, end: conversationState.isLoading ? 0.5 : 1.0),
          duration: const Duration(milliseconds: 800),
          curve: Curves.easeInOut,
          builder: (context, opacity, child) {
            return AnimatedBuilder(
              animation: _glowAnimationController,
              builder: (context, child) {
                // Gentle fade-in only (no jitter, no scale)
                final fadeOpacity = opacity * (0.85 + (_glowAnimation.value * 0.15));
                
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

    return MouseRegion(
      onEnter: hasMessages ? (_) => setState(() => _showConversationActions = true) : null,
      onExit: hasMessages ? (_) => setState(() => _showConversationActions = false) : null,
      child: Column(
        children: [
          Expanded(
            child: ShaderMask(
              shaderCallback: (Rect bounds) {
                return LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: const [
                    Colors.transparent,
                    Colors.black,
                    Colors.black,
                    Colors.transparent,
                  ],
            stops: const [0.0, 0.15, 0.85, 1.0],
          ).createShader(bounds);
        },
        blendMode: BlendMode.dstIn,
        child: ScrollConfiguration(
          behavior: ScrollConfiguration.of(context).copyWith(scrollbars: false),
          child: Scrollbar(
            controller: _conversationController,
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
                controller: _conversationController,
                reverse: true, // Bottom-to-top scroll for chat
                padding: const EdgeInsets.all(24),
                itemCount: conversationState.messages.length,
                itemBuilder: (context, index) {
                  // Reverse index since list is reversed
                  final reversedIndex = conversationState.messages.length - 1 - index;
                  final message = conversationState.messages[reversedIndex];
                  // Convert domain Message to presentation ConversationMessage
                  final conversationMessage = ConversationMessage(
                    id: message.id,
                    isFromAico: message.userId == 'aico',
                    message: message.content,
                    timestamp: message.timestamp,
                  );
                  
                  return _buildMessageBubble(context, theme, accentColor, conversationMessage);
                },
              ),
            ),
          ),
        ),
      ),
    ),
          
          // Drawer toolbar that slides out from under conversation container
          HomeToolbar(
            isVisible: _showConversationActions,
            hasMessages: hasMessages,
            accentColor: accentColor,
            onCopy: _handleCopyToClipboard,
            onSave: _handleSaveToFile,
            onRemember: hasMessages ? _handleRememberConversation : null,
          ),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(BuildContext context, ThemeData theme, Color accentColor, ConversationMessage message) {
    final conversationState = ref.watch(conversationProvider);
    
    // Check if this is the last message and AICO is currently thinking/processing
    final isLastMessage = conversationState.messages.isNotEmpty && 
                          conversationState.messages.last.timestamp == message.timestamp;
    
    // Show thinking particles when:
    // 1. Message is being sent (isSendingMessage)
    // 2. OR thinking content is streaming but response hasn't started yet (streamingThinking active + no content)
    // Stop particles when response content starts arriving
    final hasThinkingContent = conversationState.streamingThinking != null && 
                               conversationState.streamingThinking!.isNotEmpty;
    final responseHasStarted = message.message.isNotEmpty;
    
    final isStreamingOrProcessing = conversationState.isSendingMessage || 
                                    (hasThinkingContent && !responseHasStarted);
    
    final isThinking = message.isFromAico && 
                       isLastMessage && 
                       isStreamingOrProcessing;
    
    return InteractiveMessageBubble(
      content: message.message,
      isFromAico: message.isFromAico,
      isThinking: isThinking,
      timestamp: message.timestamp,
      accentColor: accentColor,
      messageId: message.id,
      conversationId: conversationState.currentConversationId,
      onFeedback: message.isFromAico && message.id != null
          ? (isPositive) => _handleFeedback(message.id!, isPositive)
          : null,
    );
  }

  // Helper methods
  void _sendMessage(String text) async {
    await HomeScreenHelpers.sendMessage(
      ref: ref,
      text: text,
      controller: _messageController,
      focusNode: _messageFocusNode,
      sendButtonKey: _sendButtonKey,
    );
  }

  /// Handle behavioral feedback submission
  Future<void> _handleFeedback(String messageId, bool isPositive) async {
    final theme = Theme.of(context);
    final accentColor = theme.colorScheme.primary;
    
    // Submit immediate feedback (thumbs only)
    final success = await ref.read(behavioralFeedbackProvider.notifier).submitFeedback(
      messageId: messageId,
      isPositive: isPositive,
    );
    
    if (!success) {
      // Show elegant glassmorphic toast for errors
      if (!mounted) return;
      GlassmorphicToast.show(
        context,
        message: 'Failed to submit feedback',
        icon: Icons.error_outline_rounded,
        accentColor: Colors.red.shade400,
        duration: const Duration(seconds: 2),
      );
      return;
    }
    
    // Show detailed feedback dialog
    if (!mounted) return;
    
    showDialog(
      context: context,
      barrierColor: Colors.transparent, // Dialog has its own backdrop
      builder: (context) => FeedbackDialog(
        isPositive: isPositive,
        messageId: messageId,
        accentColor: accentColor,
        onSubmit: (reason, freeText) async {
          // Submit detailed feedback
          await ref.read(behavioralFeedbackProvider.notifier).submitFeedback(
            messageId: messageId,
            isPositive: isPositive,
            reason: reason,
            freeText: freeText,
          );
          
          // Show elegant glassmorphic toast for success
          if (!mounted) return;
          GlassmorphicToast.show(
            context,
            message: 'Thank you for your feedback!',
            icon: Icons.check_circle_outline_rounded,
            accentColor: accentColor,
            duration: const Duration(seconds: 2),
          );
        },
      ),
    );
  }

  void _switchToPage(NavigationPage page) {
    setState(() {
      _currentPage = page;
    });
  }

  Widget _buildMainContent(BuildContext context, ThemeData theme, Color accentColor) {
    switch (_currentPage) {
      case NavigationPage.home:
        return _buildHomeContent(context, theme, accentColor);
      case NavigationPage.memory:
        return const MemoryScreen();
      case NavigationPage.admin:
        return const AdminScreen();
      case NavigationPage.settings:
        return const SettingsScreen();
    }
  }

  Widget _buildHomeContent(BuildContext context, ThemeData theme, Color accentColor) {
    final isDark = theme.brightness == Brightness.dark;
    
    return Stack(
      children: [
        // Main floating content area with organic padding
        Positioned.fill(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 20),
            child: Column(
              children: [
                // Floating avatar with ambient space
                HomeAvatarHeader(
                  accentColor: accentColor,
                  glowController: _glowAnimationController,
                  glowAnimation: _glowAnimation,
                ),
                
                const SizedBox(height: 16),
                
                // Floating conversation card
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
                    child: BackdropFilter(
                      filter: ImageFilter.blur(
                        sigmaX: GlassTheme.blurHeavy,
                        sigmaY: GlassTheme.blurHeavy,
                      ),
                      child: Container(
                        decoration: BoxDecoration(
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.04)
                              : Colors.white.withValues(alpha: 0.6),
                          borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
                          border: Border.all(
                            color: isDark
                                ? Colors.white.withValues(alpha: 0.1)
                                : Colors.white.withValues(alpha: 0.4),
                            width: 1.5,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: isDark ? 0.4 : 0.08),
                              blurRadius: 40,
                              offset: const Offset(0, 20),
                              spreadRadius: -10,
                            ),
                            if (isDark)
                              BoxShadow(
                                color: accentColor.withValues(alpha: 0.1),
                                blurRadius: 60,
                                spreadRadius: -5,
                              ),
                          ],
                        ),
                        child: _buildConversationArea(context, theme, accentColor),
                      ),
                    ),
                  ),
                ),
                
                const SizedBox(height: 16),
                
                // Floating input area
                HomeInputArea(
                  controller: _messageController,
                  focusNode: _messageFocusNode,
                  accentColor: accentColor,
                  onSend: () => _sendMessage(_messageController.text),
                  onVoice: () {}, // TODO: Implement voice input
                  sendButtonKey: _sendButtonKey,
                  voiceButtonKey: _voiceButtonKey,
                ),
              ],
            ),
          ),
        ),
        
      ],
    );
  }
  
  /// Quick copy conversation to clipboard
  Future<void> _handleCopyToClipboard() async {
    HapticFeedback.lightImpact();
    
    final handler = ConversationExportHandler(ref);
    final message = await handler.copyToClipboard();
    
    if (mounted) {
      GlassmorphicToast.show(
        context,
        message: message,
        icon: Icons.check_circle_rounded,
        accentColor: const Color(0xFFB8A1EA),
      );
    }
  }
  
  /// Save conversation to file with options
  void _handleSaveToFile() {
    HapticFeedback.mediumImpact();
    
    showDialog(
      context: context,
      barrierDismissible: true,
      barrierColor: Colors.black.withValues(alpha: 0.5),
      builder: (dialogContext) => ShareConversationModal(
        accentColor: const Color(0xFFB8A1EA),
        onExport: _exportToFile,
      ),
    );
  }
  
  /// Remember this conversation
  Future<void> _handleRememberConversation() async {
    HapticFeedback.lightImpact();
    
    final conversationState = ref.read(conversationProvider);
    if (conversationState.currentConversationId == null) return;
    if (conversationState.messages.isEmpty) return;
    
    try {
      // Use first message as title
      final firstMessage = conversationState.messages.first.content;
      final title = firstMessage.length > 60
          ? '${firstMessage.substring(0, 60)}...'
          : firstMessage;
      
      // Create full conversation text (all messages with alternating speakers)
      final fullConversation = conversationState.messages
          .asMap()
          .entries
          .map((entry) {
            // Alternate between user and AICO (odd indices = user, even = AICO)
            final speaker = entry.key.isOdd ? "AICO" : "You";
            return '$speaker: ${entry.value.content}';
          })
          .join('\n\n');
      
      // Save conversation to Memory Album
      final memoryId = await ref.read(memoryAlbumProvider.notifier).rememberConversation(
        conversationId: conversationState.currentConversationId!,
        title: title,
        summary: fullConversation, // Store FULL conversation, not truncated
      );
      
      if (memoryId != null && mounted) {
        GlassmorphicToast.show(
          context,
          message: 'Conversation saved to Memory Album',
          icon: Icons.auto_awesome_rounded,
          accentColor: const Color(0xFFD4AF37), // Gold
        );
      }
    } catch (e) {
      if (mounted) {
        GlassmorphicToast.show(
          context,
          message: 'Failed to save conversation',
          icon: Icons.error_outline_rounded,
          accentColor: const Color(0xFFED7867), // Error red
        );
      }
    }
  }
  
  /// Export conversation to file (markdown or PDF)
  Future<void> _exportToFile(ShareConversationConfig config) async {
    final handler = ConversationExportHandler(ref);
    final message = await handler.exportToFile(config);
    
    if (mounted) {
      GlassmorphicToast.show(
        context,
        message: message,
        icon: Icons.info_outline_rounded,
        accentColor: const Color(0xFFB8A1EA),
      );
    }
  }
}


