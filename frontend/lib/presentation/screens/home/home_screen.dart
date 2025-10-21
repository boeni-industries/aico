import 'dart:async';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:aico_frontend/presentation/models/conversation_message.dart';
import 'package:aico_frontend/presentation/providers/auth_provider.dart';
import 'package:aico_frontend/presentation/providers/avatar_state_provider.dart';
import 'package:aico_frontend/presentation/providers/conversation_provider.dart';
import 'package:aico_frontend/presentation/providers/settings_provider.dart';
import 'package:aico_frontend/presentation/providers/theme_provider.dart';
import 'package:aico_frontend/presentation/screens/admin/admin_screen.dart';
import 'package:aico_frontend/presentation/screens/memory/memory_screen.dart';
import 'package:aico_frontend/presentation/screens/settings/settings_screen.dart';
import 'package:aico_frontend/presentation/theme/glassmorphism.dart';
import 'package:aico_frontend/presentation/widgets/avatar/companion_avatar.dart';
import 'package:aico_frontend/presentation/widgets/chat/interactive_message_bubble.dart';
import 'package:aico_frontend/presentation/widgets/common/animated_button.dart';
import 'package:aico_frontend/presentation/widgets/thinking_display.dart';
import 'package:aico_frontend/presentation/widgets/thinking/ambient_thinking_indicator.dart';
import 'package:aico_frontend/presentation/widgets/thinking/thinking_preview_card.dart';

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
  bool _showThinkingPreview = false; // Track preview card visibility
  Timer? _hoverTimer; // Delay before showing preview
  
  // Animation controllers for immersive effects
  late AnimationController _backgroundAnimationController;
  late AnimationController _glowAnimationController;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    // Theme management now handled via Riverpod providers
    
    // Listen to text changes for typing detection
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

  Widget _buildAvatarHeader(BuildContext context, ThemeData theme, Color accentColor) {
    final conversationState = ref.watch(conversationProvider);
    final isDark = theme.brightness == Brightness.dark;
    
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
    
    // Get avatar mood color for ambient glow
    final avatarMoodColor = _getAvatarMoodColor(avatarState.mode, isDark);
    
    return AnimatedBuilder(
      animation: _glowAnimationController,
      builder: (context, child) {
        return Container(
          padding: const EdgeInsets.all(16),
          child: Container(
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              boxShadow: GlassTheme.pulsingGlow(
                color: avatarMoodColor,
                animationValue: _glowAnimation.value,
                baseIntensity: 0.2,
                pulseIntensity: 0.5,
              ),
            ),
            child: const CompanionAvatar(),
          ),
        );
      },
    );
  }

  Widget _buildConversationArea(BuildContext context, ThemeData theme, Color accentColor) {
    final conversationState = ref.watch(conversationProvider);
    final isDark = theme.brightness == Brightness.dark;
    // Avatar mood color available via _getAvatarMoodColor if needed for future features
    
    if (conversationState.isLoading) {
      return Center(
        child: Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            boxShadow: GlassTheme.ambientGlow(
              color: accentColor,
              intensity: 0.3,
              blur: 30,
            ),
          ),
          child: CircularProgressIndicator(
            color: accentColor,
            strokeWidth: 3,
          ),
        ),
      );
    }

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

    if (conversationState.messages.isEmpty) {
      return Center(
        child: AnimatedBuilder(
          animation: _glowAnimationController,
          builder: (context, child) {
            // Gentle fade-in only (no jitter, no scale)
            final fadeOpacity = 0.85 + (_glowAnimation.value * 0.15);
            
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
        ),
      );
    }

    return ShaderMask(
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
            child: ListView.builder(
              controller: _conversationController,
              padding: const EdgeInsets.all(24),
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
    );
  }

  Widget _buildInputArea(BuildContext context, ThemeData theme, Color accentColor) {
    final isDark = theme.brightness == Brightness.dark;
    final conversationState = ref.watch(conversationProvider);
    final isActive = conversationState.isSendingMessage || conversationState.isStreaming;
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 0, vertical: 12),
      child: AnimatedBuilder(
        animation: _glowAnimationController,
        builder: (context, child) {
          return ClipRRect(
            borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
            child: BackdropFilter(
              filter: ImageFilter.blur(
                sigmaX: GlassTheme.blurHeavy,
                sigmaY: GlassTheme.blurHeavy,
              ),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                decoration: BoxDecoration(
                  // Immersive frosted glass
                  color: isDark 
                      ? Colors.white.withValues(alpha: 0.06)
                      : Colors.white.withValues(alpha: 0.7),
                  borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
                  // Luminous border
                  border: Border.all(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.12)
                        : Colors.white.withValues(alpha: 0.5),
                    width: 1.5,
                  ),
                  // Subtle ambient glow when active
                  boxShadow: [
                    if (isActive) ...
                      GlassTheme.pulsingGlow(
                        color: accentColor,
                        animationValue: _glowAnimation.value,
                        baseIntensity: 0.08,  // Much more subtle
                        pulseIntensity: 0.15, // Reduced from 0.4
                      ),
                    BoxShadow(
                      color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.08),
                      blurRadius: 32,
                      offset: const Offset(0, 12),
                      spreadRadius: -8,
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
                        maxLines: null,
                        textInputAction: TextInputAction.send,
                        decoration: InputDecoration(
                          hintText: 'Share what\'s on your mind...',
                          border: InputBorder.none,
                          hintStyle: TextStyle(
                            color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                            fontSize: 15,
                            letterSpacing: 0.3,
                          ),
                        ),
                        style: const TextStyle(
                          fontSize: 15,
                          height: 1.5,
                          letterSpacing: 0.2,
                        ),
                        onSubmitted: _sendMessage,
                        onEditingComplete: () {
                          final text = _messageController.text.trim();
                          if (text.isNotEmpty) {
                            _sendMessage(text);
                          }
                        },
                      ),
                    ),
                    const SizedBox(width: 16),
                    // Modern button container with depth
                    Container(
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(28),
                        // Subtle gradient background
                        gradient: LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            accentColor.withValues(alpha: 0.12),
                            accentColor.withValues(alpha: 0.06),
                          ],
                        ),
                      ),
                      padding: const EdgeInsets.all(6),
                      child: Row(
                        children: [
                          // Voice button with micro-interactions
                          AnimatedButton(
                          key: _voiceButtonKey,
                          onPressed: () {
                            // Voice input - to be implemented
                          },
                          icon: Icons.mic_rounded,
                          size: 48,
                          borderRadius: 24,
                          backgroundColor: isDark
                              ? accentColor.withValues(alpha: 0.15)
                              : accentColor.withValues(alpha: 0.12),
                          foregroundColor: accentColor,
                          tooltip: 'Voice input',
                        ),
                        const SizedBox(width: 12),
                        // Send button - primary action (more prominent when enabled)
                        AnimatedButton(
                          key: _sendButtonKey,
                          onPressed: () {
                            final text = _messageController.text.trim();
                            if (text.isEmpty) {
                              // Trigger error shake if empty
                              final state = _sendButtonKey.currentState;
                              if (state != null && state.mounted) {
                                (state as dynamic).showError();
                              }
                            } else {
                              _sendMessage(text);
                            }
                          },
                          icon: Icons.send_rounded,
                          successIcon: Icons.check_rounded,
                          size: 48,
                          borderRadius: 24,
                          // Primary: uses accent color for both bg and icon
                          backgroundColor: isDark
                              ? accentColor.withValues(alpha: 0.20)  // Slightly more opaque
                              : accentColor.withValues(alpha: 0.18),
                          foregroundColor: accentColor,  // Same color as voice button
                          tooltip: 'Send message',
                          isEnabled: _messageController.text.trim().isNotEmpty,
                        ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildRightDrawer(BuildContext context, ThemeData theme, Color accentColor) {
    final isDark = theme.brightness == Brightness.dark;
    
    return Consumer(
      builder: (context, ref, child) {
        final conversationState = ref.watch(conversationProvider);
        final isActivelyThinking = conversationState.streamingThinking != null && 
                                   conversationState.streamingThinking!.isNotEmpty;
        
        return Padding(
          padding: const EdgeInsets.all(16.0),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
            child: AnimatedBuilder(
              animation: _glowAnimationController,
              builder: (context, child) {
                // Beautiful breathing effect - glass becomes more/less frosted
                final pulseValue = _glowAnimation.value;
                final blurIntensity = isActivelyThinking
                    ? GlassTheme.blurHeavy + (pulseValue * 6.0) // 20 → 26 breathing
                    : GlassTheme.blurHeavy;
                
                final glassOpacity = isActivelyThinking
                    ? (isDark ? 0.04 : 0.6) + (pulseValue * (isDark ? 0.02 : 0.08))
                    : (isDark ? 0.04 : 0.6);
                
                final borderOpacity = isActivelyThinking
                    ? (isDark ? 0.1 : 0.4) + (pulseValue * 0.15)
                    : (isDark ? 0.1 : 0.4);
                
                return BackdropFilter(
                  filter: ImageFilter.blur(
                    sigmaX: blurIntensity,
                    sigmaY: blurIntensity,
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
                    clipBehavior: Clip.hardEdge,
                    child: Container(
                      width: _isRightDrawerExpanded ? 300 : 72,
                      decoration: BoxDecoration(
                        // Frosted glass with breathing pulse
                        color: isDark
                            ? Colors.white.withValues(alpha: glassOpacity)
                            : Colors.white.withValues(alpha: glassOpacity),
                        borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
                        border: Border.all(
                          color: isDark
                              ? Colors.white.withValues(alpha: borderOpacity)
                              : Colors.white.withValues(alpha: borderOpacity),
                          width: 1.5,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: isDark ? 0.4 : 0.08),
                            blurRadius: 40,
                            offset: const Offset(-8, 0),
                            spreadRadius: -10,
                          ),
                          if (isDark)
                            BoxShadow(
                              color: accentColor.withValues(alpha: 0.08 + (isActivelyThinking ? pulseValue * 0.06 : 0.0)),
                              blurRadius: 60 + (isActivelyThinking ? pulseValue * 20 : 0.0),
                              spreadRadius: -5,
                            ),
                        ],
                      ),
                      child: SafeArea(
                        child: Column(
                          children: [
                            // Thinking display section (header integrated into ThinkingDisplay widget)
                            Expanded(
                              child: Consumer(
                                  builder: (context, ref, child) {
                                    final conversationState = ref.watch(conversationProvider);
                                    final settings = ref.watch(settingsProvider);
                                    
                                    if (!settings.showThinking) {
                                      return _isRightDrawerExpanded
                                          ? Center(
                                              child: Text(
                                                'Thinking display disabled in settings',
                                                style: theme.textTheme.bodySmall?.copyWith(
                                                  color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                                                ),
                                              ),
                                            )
                                          : const SizedBox.shrink();
                                    }
                                    
                                    // Show different content based on expanded state
                                    // Check if actively thinking (not just streaming response)
                                    final isActivelyThinking = conversationState.streamingThinking != null && 
                                                               conversationState.streamingThinking!.isNotEmpty;
                                    
                                    return AnimatedSwitcher(
                                      duration: const Duration(milliseconds: 300),
                                      transitionBuilder: (child, animation) {
                                        return FadeTransition(
                                          opacity: animation,
                                          child: SlideTransition(
                                            position: Tween<Offset>(
                                              begin: const Offset(0.1, 0),
                                              end: Offset.zero,
                                            ).animate(CurvedAnimation(
                                              parent: animation,
                                              curve: Curves.easeOutCubic,
                                            )),
                                            child: child,
                                          ),
                                        );
                                      },
                                      child: _isRightDrawerExpanded
                                          ? ThinkingDisplay(
                                              key: const ValueKey('expanded'),
                                              thinkingHistory: conversationState.thinkingHistory,
                                              currentThinking: conversationState.streamingThinking,
                                              isStreaming: isActivelyThinking,
                                              scrollToMessageId: _scrollToThoughtId,
                                              onCollapse: () {
                                                setState(() => _isRightDrawerExpanded = false);
                                              },
                                            )
                                          : Container(
                                              key: const ValueKey('collapsed'),
                                              child: _buildNewCollapsedIndicator(
                                                context,
                                                conversationState,
                                                isActivelyThinking,
                                              ),
                                            ),
                                    );
                                  },
                                ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
        );
      },
    );
  }

  /// New three-layer progressive disclosure thinking indicator
  /// Layer 1: Ambient indicator (bar + badge + icon)
  /// Layer 2: Preview card on hover
  /// Layer 3: Full drawer expansion
  Widget _buildNewCollapsedIndicator(
    BuildContext context,
    ConversationState conversationState,
    bool isStreaming,
  ) {
    return GestureDetector(
      onTap: () {
        setState(() {
          _isRightDrawerExpanded = true;
          _showThinkingPreview = false;
        });
      },
      child: Stack(
        children: [
          // Layer 1: Ambient Thinking Indicator
          Positioned(
            left: 0,
            top: 0,
            bottom: 0,
            child: AmbientThinkingIndicator(
              key: const ValueKey('ambient_indicator'), // Stable key to preserve widget state
              isStreaming: isStreaming,
              thoughtCount: conversationState.thinkingHistory.length,
              onTap: () {
                setState(() {
                  _isRightDrawerExpanded = true;
                  _showThinkingPreview = false;
                });
              },
              onHoverStart: () {
                // Start timer for delayed preview
                _hoverTimer?.cancel();
                _hoverTimer = Timer(const Duration(milliseconds: 300), () {
                  if (mounted) {
                    setState(() => _showThinkingPreview = true);
                  }
                });
              },
              onHoverEnd: () {
                // Cancel timer and hide preview
                _hoverTimer?.cancel();
                setState(() => _showThinkingPreview = false);
              },
            ),
          ),

        // Layer 2: Preview Card (on hover) - positioned to overlay conversation area
        if (_showThinkingPreview)
          Positioned(
            left: -296, // Position to the left of the drawer (280px card + 16px spacing)
            top: 0,
            bottom: 0,
            child: Align(
              alignment: Alignment.center,
              child: TweenAnimationBuilder<Offset>(
                duration: const Duration(milliseconds: 200),
                curve: Curves.easeOut,
                tween: Tween<Offset>(
                  begin: const Offset(20, 0), // Slide from right
                  end: Offset.zero,
                ),
                builder: (context, offset, child) {
                  return Transform.translate(
                    offset: offset,
                    child: FadeTransition(
                      opacity: AlwaysStoppedAnimation(
                        1.0 - (offset.dx / 20.0).clamp(0.0, 1.0),
                      ),
                      child: child,
                    ),
                  );
                },
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 60), // Vertical padding to avoid screen edges
                  child: MouseRegion(
                    onEnter: (_) {
                      // Keep preview visible when hovering over it
                      _hoverTimer?.cancel();
                    },
                    onExit: (_) {
                      // Hide preview when leaving
                      setState(() => _showThinkingPreview = false);
                    },
                    child: ThinkingPreviewCard(
                      recentThoughts: conversationState.thinkingHistory,
                      streamingThought: conversationState.streamingThinking,
                      isStreaming: isStreaming,
                      onExpand: () {
                        setState(() {
                          _isRightDrawerExpanded = true;
                          _showThinkingPreview = false;
                        });
                      },
                    ),
                  ),
                ),
              ),
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

  void _sendMessage(String text) async {
    final trimmedText = text.trim();
    if (trimmedText.isEmpty) return;
    
    // Clear input immediately for better UX
    _messageController.clear();
    _messageFocusNode.requestFocus();
    
    // Show success animation immediately after send
    Future.delayed(const Duration(milliseconds: 100), () {
      final state = _sendButtonKey.currentState;
      if (state != null && state.mounted) {
        (state as dynamic).showSuccess();
      }
    });
    
    // Send message via provider with streaming enabled (don't await before success animation)
    await ref.read(conversationProvider.notifier).sendMessage(trimmedText, stream: true);
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
    
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
        child: BackdropFilter(
          filter: ImageFilter.blur(
            sigmaX: GlassTheme.blurHeavy,
            sigmaY: GlassTheme.blurHeavy,
          ),
          child: Container(
            width: _isLeftDrawerExpanded ? 240 : 72,
            decoration: BoxDecoration(
              // Frosted glass with organic shape
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
                  offset: const Offset(8, 0),
                  spreadRadius: -10,
                ),
                if (isDark)
                  BoxShadow(
                    color: accentColor.withValues(alpha: 0.08),
                    blurRadius: 60,
                    spreadRadius: -5,
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
                          _buildToggleItem(context, theme, accentColor),
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
                          top: BorderSide(color: theme.dividerColor),
                        ),
                      ),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          // Theme toggle removed - dark mode only
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
          ),
        ),
      );
  }

  Widget _buildToggleItem(BuildContext context, ThemeData theme, Color accentColor) {
    if (!_isLeftDrawerExpanded) {
      // Collapsed mode - just the burger icon
      return Container(
        margin: const EdgeInsets.only(bottom: 8),
        child: IconButton(
          onPressed: () => setState(() => _isLeftDrawerExpanded = true),
          icon: Icon(
            Icons.menu,
            color: accentColor.withValues(alpha: 0.6),
            size: 20,
          ),
          tooltip: 'Expand menu',
          style: IconButton.styleFrom(
            padding: EdgeInsets.zero,
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
              color: accentColor.withValues(alpha: 0.6),
              size: 20,
            ),
            tooltip: 'Collapse menu',
            style: IconButton.styleFrom(
              padding: EdgeInsets.zero,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNavItem(BuildContext context, ThemeData theme, Color accentColor, IconData icon, String title, bool isActive, VoidCallback onTap) {
    if (!_isLeftDrawerExpanded) {
      // Collapsed mode - subtle icon-only button
      return Container(
        margin: const EdgeInsets.only(bottom: 8),
        child: Tooltip(
          message: title,
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: onTap,
              borderRadius: BorderRadius.circular(12),
              child: Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  // Only show background for active state
                  color: isActive ? accentColor.withValues(alpha: 0.15) : null,
                  border: isActive ? Border.all(
                    color: accentColor.withValues(alpha: 0.3),
                    width: 1,
                  ) : null,
                ),
                child: Icon(
                  icon,
                  size: 20,
                  color: isActive ? accentColor : accentColor.withValues(alpha: 0.6),
                ),
              ),
            ),
          ),
        ),
      );
    }
    
    // Expanded mode - subtle list tile
    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              color: isActive ? accentColor.withValues(alpha: 0.15) : null,
              border: isActive ? Border.all(
                color: accentColor.withValues(alpha: 0.3),
                width: 1,
              ) : null,
            ),
            child: Row(
              children: [
                Icon(
                  icon,
                  size: 20,
                  color: isActive ? accentColor : accentColor.withValues(alpha: 0.6),
                ),
                const SizedBox(width: 12),
                Text(
                  title,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: isActive ? accentColor : theme.colorScheme.onSurface.withValues(alpha: 0.7),
                    fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
                  ),
                ),
              ],
            ),
          ),
        ),
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
      // Collapsed mode - subtle icon only
      return Container(
        margin: const EdgeInsets.only(bottom: 4),
        child: Tooltip(
          message: tooltip,
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: onTap,
              borderRadius: BorderRadius.circular(12),
              child: Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                ),
                child: icon,
              ),
            ),
          ),
        ),
      );
    }

    // Expanded mode - subtle list tile
    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                icon,
                const SizedBox(width: 12),
                Text(
                  tooltip,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
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
                _buildAvatarHeader(context, theme, accentColor),
                
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
                _buildInputArea(context, theme, accentColor),
              ],
            ),
          ),
        ),
      ],
    );
  }
}


