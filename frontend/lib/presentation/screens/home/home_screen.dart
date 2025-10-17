import 'dart:async';
import 'dart:ui';
import 'package:aico_frontend/presentation/models/conversation_message.dart';
import 'package:aico_frontend/presentation/providers/auth_provider.dart';
import 'package:aico_frontend/presentation/providers/avatar_state_provider.dart';
import 'package:aico_frontend/presentation/providers/conversation_provider.dart';
import 'package:aico_frontend/presentation/providers/settings_provider.dart';
import 'package:aico_frontend/presentation/providers/theme_provider.dart';
import 'package:aico_frontend/presentation/screens/admin/admin_screen.dart';
import 'package:aico_frontend/presentation/screens/memory/memory_screen.dart';
import 'package:aico_frontend/presentation/screens/settings/settings_screen.dart';
import 'package:aico_frontend/presentation/widgets/avatar/companion_avatar.dart';
import 'package:aico_frontend/presentation/widgets/chat/message_bubble.dart';
import 'package:aico_frontend/presentation/widgets/thinking_display.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Home screen featuring avatar-centric hub with integrated conversation interface.
/// Serves as the primary interaction point with AICO, including conversation history
/// and collapsible right drawer for thoughts and memory timeline.
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

enum NavigationPage {
  home,
  memory,
  admin,
  settings,
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  bool _isRightDrawerOpen = true;
  bool _isRightDrawerExpanded = false; // true = expanded, false = collapsed to icons
  bool _isLeftDrawerExpanded = true; // true = expanded with text, false = collapsed to icons only
  NavigationPage _currentPage = NavigationPage.home;
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _conversationController = ScrollController();
  final FocusNode _messageFocusNode = FocusNode();
  Timer? _typingTimer;
  bool _isUserTyping = false;

  @override
  void initState() {
    super.initState();
    // Theme management now handled via Riverpod providers
    
    // Listen to text changes for typing detection
    _messageController.addListener(_onTypingChanged);
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
    _messageController.removeListener(_onTypingChanged);
    _messageController.dispose();
    _conversationController.dispose();
    _messageFocusNode.dispose();
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
    final avatarMoodColor = _getAvatarMoodColor(avatarState.mode, theme.brightness == Brightness.dark);
    
    // Listen for conversation changes to auto-scroll
    ref.listen<ConversationState>(conversationProvider, (previous, next) {
      // Auto-scroll when new messages are added OR when content/thinking changes (streaming)
      if (previous != null) {
        bool shouldScroll = false;
        
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
        
        if (shouldScroll) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            _scrollToBottom();
          });
        }
      }
    });
    
    return Scaffold(
        body: Container(
          // Atmospheric background with avatar mood radiation
          decoration: BoxDecoration(
            gradient: RadialGradient(
              center: const Alignment(0.0, -0.6), // Avatar position
              radius: 1.5,
              colors: theme.brightness == Brightness.dark
                  ? [
                      // Dark mode: avatar mood radiates into space
                      Color.lerp(const Color(0xFF181A21), avatarMoodColor, 0.08)!,
                      const Color(0xFF181A21),
                      const Color(0xFF0F1015), // Darker edges for depth
                    ]
                  : [
                      // Light mode: subtle mood tint
                      Color.lerp(const Color(0xFFF5F6FA), avatarMoodColor, 0.03)!,
                      const Color(0xFFF5F6FA),
                      const Color(0xFFEEEFF3),
                    ],
              stops: const [0.0, 0.5, 1.0],
            ),
          ),
          child: Stack(
          children: [
            Row(
              children: [
                // Left drawer for navigation - always visible on desktop, toggles between expanded/collapsed
                if (isDesktop)
                  _buildLeftDrawer(context, theme, accentColor),
            
            // Main content area - switches based on selected page
            Expanded(
              flex: (_isRightDrawerOpen && isDesktop) ? 2 : 3,
              child: SafeArea(
                child: _buildMainContent(context, theme, accentColor),
              ),
            ),
            
                // Right drawer for thoughts and memory - always visible on desktop, toggles between expanded/collapsed
                if (_isRightDrawerOpen && isDesktop)
                  _buildRightDrawer(context, theme, accentColor),
              ],
            ),
          ],
        ), // Close Stack
      ), // Close body
      floatingActionButton: Stack(
        children: [
        // Right drawer toggle - always positioned on drawer edge, vertically centered
        if (isDesktop && _isRightDrawerOpen)
          Positioned(
            right: _isRightDrawerExpanded ? 284 : 56, // Stick to drawer edge with proper offset
            top: MediaQuery.of(context).size.height / 2 - 24, // Always vertically centered
            child: Container(
              decoration: BoxDecoration(
                color: theme.colorScheme.surface,
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(12),
                  bottomLeft: Radius.circular(12),
                ),
                border: Border.all(
                  color: theme.dividerColor.withValues(alpha: 0.2),
                ),
              ),
              child: IconButton(
                onPressed: () => setState(() => _isRightDrawerExpanded = !_isRightDrawerExpanded),
                icon: Icon(_isRightDrawerExpanded ? Icons.chevron_right : Icons.chevron_left),
                tooltip: _isRightDrawerExpanded ? 'Collapse thoughts' : 'Expand thoughts',
                style: IconButton.styleFrom(
                  foregroundColor: theme.colorScheme.onSurface,
                ),
              ),
            ),
          ),
        
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
                icon: const Icon(Icons.chevron_left),
                tooltip: 'Show AICO\'s thoughts',
                style: IconButton.styleFrom(
                  foregroundColor: theme.colorScheme.onSurface,
                ),
              ),
            ),
          ),
        ],
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.endTop,
    ); // Close Scaffold
  }

  Widget _buildAvatarHeader(BuildContext context, ThemeData theme, Color accentColor) {
    final conversationState = ref.watch(conversationProvider);
    
    // Update avatar state based on conversation state
    final avatarState = ref.watch(avatarRingStateProvider);
    final isThinking = conversationState.isSendingMessage || conversationState.isStreaming;
    
    // Sync avatar mode with thinking state
    if (isThinking && avatarState.mode != AvatarMode.thinking) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(avatarRingStateProvider.notifier).startThinking(intensity: 0.8);
      });
    } else if (!isThinking && avatarState.mode == AvatarMode.thinking) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(avatarRingStateProvider.notifier).returnToIdle();
      });
    }
    
    return Container(
      padding: const EdgeInsets.all(24),
      child: const CompanionAvatar(),
    );
  }

  Widget _buildConversationArea(BuildContext context, ThemeData theme, Color accentColor) {
    final conversationState = ref.watch(conversationProvider);
    
    if (conversationState.isLoading) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (conversationState.error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 48,
              color: theme.colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              'Error loading conversation',
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              conversationState.error!,
              style: theme.textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => ref.read(conversationProvider.notifier).clearError(),
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 24),
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
            child: Padding(
              padding: const EdgeInsets.only(right: 16), // Add padding to prevent scrollbar overlap
              child: ListView.builder(
                controller: _conversationController,
                itemCount: conversationState.messages.length,
                itemBuilder: (context, index) {
                  final message = conversationState.messages[index];
                  // Convert domain Message to presentation ConversationMessage
                  final conversationMessage = ConversationMessage(
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
    );
  }

  Widget _buildMessageBubble(BuildContext context, ThemeData theme, Color accentColor, ConversationMessage message) {
    final conversationState = ref.watch(conversationProvider);
    
    // Check if this is the last message and AICO is currently thinking/processing
    final isLastMessage = conversationState.messages.isNotEmpty && 
                          conversationState.messages.last.timestamp == message.timestamp;
    
    // Show thinking particles when:
    // 1. Thinking content is streaming (inner monologue)
    // 2. OR response is streaming (actual answer being generated)
    // 3. OR we have thinking content but message is still empty/incomplete
    // This ensures particles appear as soon as thinking starts and continue until response is complete
    final hasThinkingContent = conversationState.streamingThinking != null && 
                               conversationState.streamingThinking!.isNotEmpty;
    final isStreamingOrProcessing = conversationState.isSendingMessage || 
                                    conversationState.isStreaming ||
                                    hasThinkingContent;
    
    final isThinking = message.isFromAico && 
                       isLastMessage && 
                       isStreamingOrProcessing;
    
    return MessageBubble(
      content: message.message,
      isFromAico: message.isFromAico,
      isThinking: isThinking,
      timestamp: message.timestamp,
      accentColor: accentColor,
    );
  }

  Widget _buildInputArea(BuildContext context, ThemeData theme, Color accentColor) {
    final isDark = theme.brightness == Brightness.dark;
    
    return Container(
      padding: const EdgeInsets.all(24),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 30, sigmaY: 30), // Stronger blur for more depth
          child: Stack(
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  // Very transparent for frost effect + glow shine-through
                  color: isDark 
                      ? theme.colorScheme.surfaceContainerHighest.withOpacity(0.3)
                      : theme.colorScheme.surface.withOpacity(0.5),
                  borderRadius: BorderRadius.circular(24),
                  // Frosted glass border
                  border: Border.all(
                    color: isDark
                        ? Colors.white.withOpacity(0.1)
                        : Colors.white.withOpacity(0.3),
                    width: 1.5,
                  ),
                  // Soft glow effect
                  boxShadow: [
                    if (isDark)
                      BoxShadow(
                        color: theme.colorScheme.outline.withOpacity(0.1),
                        blurRadius: 12,
                        spreadRadius: 0,
                      )
                    else
                      BoxShadow(
                        color: theme.colorScheme.shadow.withOpacity(0.1),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                  ],
                ),
                child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: _messageController,
                focusNode: _messageFocusNode,
                autofocus: true,
                decoration: InputDecoration(
                  hintText: 'Share what\'s on your mind...',
                  border: InputBorder.none,
                  hintStyle: TextStyle(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                  ),
                ),
                onSubmitted: _sendMessage,
              ),
            ),
            const SizedBox(width: 12),
            Row(
              children: [
                IconButton(
                  onPressed: () {},
                  icon: const Icon(Icons.mic),
                  style: IconButton.styleFrom(
                    backgroundColor: accentColor.withValues(alpha: 0.1),
                    foregroundColor: accentColor,
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  onPressed: () => _sendMessage(_messageController.text),
                  icon: const Icon(Icons.send),
                  style: IconButton.styleFrom(
                    backgroundColor: accentColor,
                    foregroundColor: Colors.white,
                  ),
                ),
              ],
            ),
          ],
        ),
                ),
                // Grain texture overlay for frosted glass effect
                Positioned.fill(
                  child: IgnorePointer(
                    child: Opacity(
                      opacity: isDark ? 0.25 : 0.20,
                      child: Container(
                        decoration: const BoxDecoration(
                          image: DecorationImage(
                            image: AssetImage('assets/images/noise_tile.png'),
                            repeat: ImageRepeat.repeat,
                            filterQuality: FilterQuality.medium,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
    );
  }

  Widget _buildRightDrawer(BuildContext context, ThemeData theme, Color accentColor) {
    final isDark = theme.brightness == Brightness.dark;
    
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20), // Match left drawer blur strength
        child: Stack(
          children: [
            Container(
              width: _isRightDrawerExpanded ? 300 : 72,
              decoration: BoxDecoration(
                // Very transparent for frost effect + glow shine-through
                color: isDark
                    ? theme.colorScheme.surface.withOpacity(0.3)
                    : theme.colorScheme.surface.withOpacity(0.5),
                border: Border(
                  left: BorderSide(
                    color: isDark
                        ? Colors.white.withOpacity(0.1) // Frosted glass edge
                        : Colors.white.withOpacity(0.3),
                    width: 1.5,
                  ),
                ),
                // Enhanced shadows for depth
                boxShadow: isDark ? [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.3),
                    blurRadius: 20,
                    spreadRadius: 0,
                    offset: const Offset(0, 4),
                  ),
                  BoxShadow(
                    color: theme.colorScheme.outline.withOpacity(0.1),
                    blurRadius: 8,
                    spreadRadius: 0,
                  ),
                ] : [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.15),
                    blurRadius: 16,
                    offset: const Offset(0, 4),
                  ),
                  BoxShadow(
                    color: theme.colorScheme.shadow.withOpacity(0.05),
                    blurRadius: 8,
                    offset: const Offset(-2, 0),
                  ),
                ],
              ),
              child: SafeArea(
                child: Column(
                  children: [
                    // Thinking display section (header integrated into ThinkingDisplay widget)
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.only(bottom: 24), // Add bottom padding for even spacing
                        child: _isRightDrawerExpanded
                            ? Consumer(
                                builder: (context, ref, child) {
                                  final conversationState = ref.watch(conversationProvider);
                                  final settings = ref.watch(settingsProvider);
                                  
                                  // Following AICO guidelines: Data from provider (Single Source of Truth)
                                  // No need for Visibility hack - widget is stateless presentation
                                  if (!settings.showThinking) {
                                    return Center(
                                      child: Text(
                                        'Thinking display disabled in settings',
                                        style: theme.textTheme.bodySmall?.copyWith(
                                          color: theme.colorScheme.onSurface.withOpacity(0.5),
                                        ),
                                      ),
                                    );
                                  }
                                  
                                  return ThinkingDisplay(
                                    thinkingHistory: conversationState.thinkingHistory,
                                    currentThinking: conversationState.streamingThinking,
                                    isStreaming: conversationState.isStreaming,
                                  );
                                },
                              )
                            : const SizedBox.shrink(),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            // Grain texture overlay for frosted glass effect
            Positioned.fill(
              child: IgnorePointer(
                child: Opacity(
                  opacity: isDark ? 0.12 : 0.08,
                  child: Container(
                    decoration: const BoxDecoration(
                      image: DecorationImage(
                        image: AssetImage('assets/images/noise_tile.png'),
                        repeat: ImageRepeat.repeat,
                        filterQuality: FilterQuality.medium,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildThoughtCard(BuildContext context, ThemeData theme, Color accentColor, {
    required String type,
    required String message,
  }) {
    final icons = {
      'Suggestion': Icons.lightbulb_outline,
      'Reminder': Icons.event_note,
      'Memory': Icons.auto_stories,
    };
    
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: accentColor.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: accentColor.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icons[type], size: 16, color: accentColor),
              const SizedBox(width: 6),
              Text(
                type,
                style: theme.textTheme.labelSmall?.copyWith(
                  color: accentColor,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const Spacer(),
              Icon(Icons.close, size: 14, color: theme.colorScheme.onSurface.withValues(alpha: 0.4)),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            message,
            style: theme.textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  Widget _buildMemoryItem(BuildContext context, ThemeData theme, Color accentColor, {
    required String title,
    required String time,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: theme.dividerColor.withValues(alpha: 0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: theme.textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            time,
            style: theme.textTheme.labelSmall?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
            ),
          ),
        ],
      ),
    );
  }


  /// Get avatar mood color for atmospheric lighting
  Color _getAvatarMoodColor(AvatarMode mode, bool isDark) {
    const coral = Color(0xFFED7867);
    const emerald = Color(0xFF10B981);
    const amber = Color(0xFFF59E0B);
    const sapphire = Color(0xFF3B82F6);
    const purple = Color(0xFFB8A1EA);
    const violet = Color(0xFF8B5CF6);
    
    switch (mode) {
      case AvatarMode.thinking:
        return purple;
      case AvatarMode.processing:
        return violet;
      case AvatarMode.listening:
        return sapphire;
      case AvatarMode.speaking:
        return purple;
      case AvatarMode.success:
        return emerald;
      case AvatarMode.error:
        return coral;
      case AvatarMode.attention:
        return amber;
      case AvatarMode.connecting:
        return sapphire;
      case AvatarMode.idle:
        return emerald;
    }
  }

  void _sendMessage(String text) {
    if (text.trim().isEmpty) return;
    
    // Cancel typing timer and transition to thinking
    _typingTimer?.cancel();
    setState(() => _isUserTyping = false);
    
    // Clear the input field immediately
    _messageController.clear();
    
    // Transition avatar from listening to thinking (smooth transition)
    ref.read(avatarRingStateProvider.notifier).startThinking(intensity: 0.8);
    
    // Send message through conversation provider with streaming enabled
    ref.read(conversationProvider.notifier).sendMessage(text.trim(), stream: true);
    
    // Scroll to bottom after sending
    _scrollToBottom();
    
    // Refocus the input field for continuous conversation
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _messageFocusNode.requestFocus();
    });
  }

  void _scrollToBottom() {
    // Use a slight delay to ensure content is fully rendered
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Future.delayed(const Duration(milliseconds: 50), () {
        if (_conversationController.hasClients) {
          _conversationController.animateTo(
            _conversationController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeOut,
          );
        }
      });
    });
  }


  Widget _buildLeftDrawer(BuildContext context, ThemeData theme, Color accentColor) {
    final isDark = theme.brightness == Brightness.dark;
    
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20), // Stronger blur for visible frost
        child: Stack(
          children: [
            Container(
              width: _isLeftDrawerExpanded ? 240 : 72,
              decoration: BoxDecoration(
                // Very transparent for frost effect + glow shine-through
                color: isDark
                    ? theme.colorScheme.surface.withOpacity(0.3)
                    : theme.colorScheme.surface.withOpacity(0.5),
                border: Border(
                  right: BorderSide(
                    color: isDark 
                        ? Colors.white.withOpacity(0.1) // Frosted glass edge
                        : Colors.white.withOpacity(0.3),
                    width: 1.5,
                  ),
                ),
            // Enhanced shadows for depth
            boxShadow: isDark ? [
              BoxShadow(
                color: Colors.black.withOpacity(0.3),
                blurRadius: 20,
                spreadRadius: 0,
                offset: const Offset(0, 4),
              ),
              BoxShadow(
                color: theme.colorScheme.outline.withOpacity(0.1),
                blurRadius: 8,
                spreadRadius: 0,
              ),
            ] : [
              BoxShadow(
                color: Colors.black.withOpacity(0.15),
                blurRadius: 16,
                offset: const Offset(0, 4),
              ),
              BoxShadow(
                color: theme.colorScheme.shadow.withOpacity(0.05),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: SafeArea(
            child: Column(
              children: [
                // Main navigation items
                Expanded(
                  child: ListView(
                    padding: EdgeInsets.symmetric(horizontal: _isLeftDrawerExpanded ? 16 : 8, vertical: 8),
                    children: [
                      // Toggle button as first nav item
                      _buildToggleItem(context, theme),
                      const SizedBox(height: 8),
                      _buildNavItem(context, theme, accentColor, Icons.home, 'Home', _currentPage == NavigationPage.home, () => _switchToPage(NavigationPage.home)),
                      const SizedBox(height: 8),
                      _buildNavItem(context, theme, accentColor, Icons.auto_stories, 'Memory', _currentPage == NavigationPage.memory, () => _switchToPage(NavigationPage.memory)),
                      _buildNavItem(context, theme, accentColor, Icons.admin_panel_settings, 'Admin', _currentPage == NavigationPage.admin, () => _switchToPage(NavigationPage.admin)),
                      _buildNavItem(context, theme, accentColor, Icons.settings, 'Settings', _currentPage == NavigationPage.settings, () => _switchToPage(NavigationPage.settings)),
                    ],
                  ),
                ),
                
                // System controls at bottom
                Container(
                  padding: EdgeInsets.symmetric(horizontal: _isLeftDrawerExpanded ? 16 : 8, vertical: 8),
                  decoration: BoxDecoration(
                    border: Border(
                      top: BorderSide(color: theme.dividerColor), // Adaptive divider
                    ),
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      _buildSystemControl(
                        context,
                        theme,
                        accentColor,
                        () async {
                          await ref.read(themeControllerProvider.notifier).toggleTheme();
                        },
                        'Theme',
                      ),
                      const SizedBox(height: 4),
                      _buildSystemControl(
                        context,
                        theme,
                        accentColor,
                        () async {
                          final currentState = ref.read(themeControllerProvider);
                          await ref.read(themeControllerProvider.notifier).setHighContrastEnabled(!currentState.isHighContrast);
                        },
                        'Contrast',
                        isContrast: true,
                      ),
                      const SizedBox(height: 4),
                      _buildSystemControl(
                        context,
                        theme,
                        accentColor,
                        () {
                          ref.read(authProvider.notifier).logout();
                        },
                        'Logout',
                        isLogout: true,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
            ),
            // Grain texture overlay for frosted glass effect
            Positioned.fill(
              child: IgnorePointer(
                child: Opacity(
                  opacity: isDark ? 0.12 : 0.08,
                  child: Container(
                    decoration: const BoxDecoration(
                      image: DecorationImage(
                        image: AssetImage('assets/images/noise_tile.png'),
                        repeat: ImageRepeat.repeat,
                        filterQuality: FilterQuality.medium,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildToggleItem(BuildContext context, ThemeData theme) {
    if (!_isLeftDrawerExpanded) {
      // Collapsed mode - just the burger icon
      return Container(
        margin: const EdgeInsets.only(bottom: 8),
        child: IconButton(
          onPressed: () => setState(() => _isLeftDrawerExpanded = true),
          icon: Icon(
            Icons.menu,
            color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
          ),
          tooltip: 'Expand menu',
          style: IconButton.styleFrom(
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
        ),
      );
    }
    
    // Expanded mode - right-aligned toggle
    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          IconButton(
            onPressed: () => setState(() => _isLeftDrawerExpanded = false),
            icon: Icon(
              Icons.menu_open,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
            ),
            tooltip: 'Collapse menu',
            style: IconButton.styleFrom(
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNavItem(BuildContext context, ThemeData theme, Color accentColor, IconData icon, String title, bool isActive, VoidCallback onTap) {
    if (!_isLeftDrawerExpanded) {
      // Collapsed mode - icon only
      return Container(
        margin: const EdgeInsets.only(bottom: 8),
        child: Tooltip(
          message: title,
          child: InkWell(
            onTap: onTap,
            borderRadius: BorderRadius.circular(8),
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(8),
                color: isActive ? accentColor.withValues(alpha: 0.1) : null,
              ),
              child: Icon(
                icon,
                color: isActive ? accentColor : theme.colorScheme.onSurface.withValues(alpha: 0.7),
              ),
            ),
          ),
        ),
      );
    }
    
    // Expanded mode - icon with text
    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      child: ListTile(
        leading: Icon(
          icon,
          color: isActive ? accentColor : theme.colorScheme.onSurface.withValues(alpha: 0.7),
        ),
        title: Text(
          title,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: isActive ? accentColor : theme.colorScheme.onSurface,
            fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
          ),
        ),
        onTap: onTap,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        tileColor: isActive ? accentColor.withValues(alpha: 0.1) : null,
        hoverColor: accentColor.withValues(alpha: 0.05),
      ),
    );
  }

  void _switchToPage(NavigationPage page) {
    setState(() {
      _currentPage = page;
    });
  }

  Widget _buildSystemControl(
    BuildContext context,
    ThemeData theme,
    Color accentColor,
    VoidCallback onTap,
    String tooltip, {
    bool isContrast = false,
    bool isLogout = false,
  }) {
    // Determine icon based on control type
    Widget icon;
    if (isContrast) {
      icon = Consumer(
        builder: (context, ref, child) {
          final themeState = ref.watch(themeControllerProvider);
          return Icon(
            Icons.contrast,
            color: themeState.isHighContrast
                ? accentColor
                : theme.colorScheme.onSurface.withValues(alpha: 0.7),
            size: 20,
          );
        },
      );
    } else if (isLogout) {
      icon = Icon(
        Icons.logout,
        color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
        size: 20,
      );
    } else {
      // Theme toggle
      icon = Consumer(
        builder: (context, ref, child) {
          final themeState = ref.watch(themeControllerProvider);
          return Icon(
            themeState.themeMode == ThemeMode.light ? Icons.wb_sunny : Icons.nightlight_round,
            color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
            size: 20,
          );
        },
      );
    }

    if (!_isLeftDrawerExpanded) {
      // Collapsed mode - icon only
      return Tooltip(
        message: tooltip,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          hoverColor: theme.colorScheme.surfaceContainerHighest, // Elevated hover state
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(8),
            ),
            child: icon,
          ),
        ),
      );
    }

    // Expanded mode - icon with text
    return ListTile(
      leading: icon,
      title: Text(
        tooltip,
        style: theme.textTheme.bodyMedium?.copyWith(
          color: theme.colorScheme.onSurface,
        ),
      ),
      onTap: onTap,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
      ),
      hoverColor: theme.colorScheme.surfaceContainerHighest, // Elevated hover state
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      dense: true,
    );
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
    return Column(
      children: [
        // Avatar and status header
        _buildAvatarHeader(context, theme, accentColor),
        
        // Conversation area
        Expanded(
          child: _buildConversationArea(context, theme, accentColor),
        ),
        
        // Input area
        _buildInputArea(context, theme, accentColor),
      ],
    );
  }
}


