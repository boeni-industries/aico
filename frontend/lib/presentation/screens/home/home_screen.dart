import 'dart:async';
import 'dart:ui';

import 'package:aico_frontend/presentation/providers/conversation_provider.dart';
import 'package:aico_frontend/presentation/providers/layout_provider.dart';
import 'package:aico_frontend/presentation/providers/memory_album_provider.dart';
import 'package:aico_frontend/presentation/screens/admin/admin_screen.dart';
import 'package:aico_frontend/presentation/screens/home/controllers/home_drawer_controller.dart' as home_drawer;
import 'package:aico_frontend/presentation/screens/home/controllers/home_navigation_controller.dart';
import 'package:aico_frontend/presentation/screens/home/controllers/home_typing_controller.dart';
import 'package:aico_frontend/presentation/screens/home/handlers/conversation_export_handler.dart';
import 'package:aico_frontend/presentation/screens/home/handlers/conversation_feedback_handler.dart';
import 'package:aico_frontend/presentation/screens/home/helpers/home_screen_helpers.dart';
import 'package:aico_frontend/presentation/screens/home/widgets/home_avatar_header.dart';
import 'package:aico_frontend/presentation/screens/home/widgets/home_background.dart';
import 'package:aico_frontend/presentation/screens/home/widgets/home_conversation_area.dart';
import 'package:aico_frontend/presentation/widgets/avatar/animated_avatar_container.dart';
import 'package:aico_frontend/presentation/widgets/layouts/modal_aware_layout.dart';
import 'package:aico_frontend/presentation/screens/home/widgets/home_input_area.dart';
import 'package:aico_frontend/presentation/screens/home/widgets/home_left_drawer.dart';
import 'package:aico_frontend/presentation/screens/home/widgets/home_right_drawer.dart';
import 'package:aico_frontend/presentation/screens/memory/memory_screen.dart';
import 'package:aico_frontend/presentation/screens/settings/settings_screen.dart';
import 'package:aico_frontend/presentation/widgets/common/glassmorphic_toast.dart';
import 'package:aico_frontend/presentation/widgets/conversation/share_conversation_modal.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// Export NavigationPage from home_left_drawer to avoid duplication
export 'package:aico_frontend/presentation/screens/home/widgets/home_left_drawer.dart' show NavigationPage;

/// Home screen featuring avatar-centric hub with integrated conversation interface.
/// Serves as the primary interaction point with AICO, including conversation history
/// and collapsible right drawer for thoughts and memory timeline.
/// 
/// Refactored for maintainability:
/// - Controllers handle state logic
/// - Widgets handle UI composition
/// - Handlers manage business logic
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> with TickerProviderStateMixin {
  // Controllers
  late final NavigationController _navigationController;
  late final home_drawer.DrawerController _drawerController;
  late TypingController _typingController;
  
  // UI Controllers
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _conversationController = ScrollController();
  final FocusNode _messageFocusNode = FocusNode();
  final GlobalKey _sendButtonKey = GlobalKey();
  final GlobalKey _voiceButtonKey = GlobalKey();
  
  // Animation controllers
  late AnimationController _backgroundAnimationController;
  late AnimationController _glowAnimationController;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    
    // Initialize controllers
    _navigationController = NavigationController();
    _drawerController = home_drawer.DrawerController();
    _typingController = TypingController(
      ref: ref,
      textController: _messageController,
    );
    
    // Initialize animation controllers
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
    
    // Listen for conversation changes to auto-scroll
    _setupConversationListener();
  }
  
  void _setupConversationListener() {
    ref.listenManual<ConversationState>(conversationProvider, (previous, next) {
      bool shouldScroll = false;
      
      // Update layout thinking state
      final isThinking = next.isSendingMessage || next.isStreaming;
      ref.read(layoutProvider.notifier).setThinking(isThinking);
      
      // Update message presence
      ref.read(layoutProvider.notifier).setHasMessages(next.messages.isNotEmpty);
      
      if (previous != null) {
        // New message added
        if (next.messages.length > previous.messages.length) {
          shouldScroll = true;
        }
        // Message content updated (streaming response)
        else if (next.messages.length == previous.messages.length && next.messages.isNotEmpty) {
          final lastMessage = next.messages.last;
          final previousLastMessage = previous.messages.isNotEmpty ? previous.messages.last : null;
          
          if (previousLastMessage != null && 
              lastMessage.content != previousLastMessage.content) {
            shouldScroll = true;
          }
        }
        // Thinking content updated (streaming inner monologue)
        if (next.isStreaming && next.streamingThinking != previous.streamingThinking) {
          shouldScroll = true;
        }
      } else {
        // Initial load from cache - scroll to bottom instantly if messages exist
        if (next.messages.isNotEmpty && !next.isLoading) {
          HomeScreenHelpers.scrollToBottom(_conversationController, instant: true);
          return;
        }
      }
      
      if (shouldScroll) {
        // Don't auto-scroll if user is actively scrolling up
        final isNearBottom = _conversationController.hasClients && 
            _conversationController.position.pixels < 200;
        if (isNearBottom || !_conversationController.hasClients) {
          HomeScreenHelpers.scrollToBottom(_conversationController);
        }
      }
    });
  }
  
  @override
  void dispose() {
    _typingController.dispose();
    _navigationController.dispose();
    _drawerController.dispose();
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
    final accentColor = const Color(0xFFB8A1EA);
    final screenWidth = MediaQuery.of(context).size.width;
    final isDesktop = screenWidth > 800;
    
    return Scaffold(
      body: HomeBackground(
        animationController: _backgroundAnimationController,
        child: Row(
          children: [
            // Left drawer for navigation
            if (isDesktop)
              ListenableBuilder(
                listenable: Listenable.merge([_navigationController, _drawerController]),
                builder: (context, _) => HomeLeftDrawer(
                  accentColor: accentColor,
                  isExpanded: _drawerController.isLeftDrawerExpanded,
                  currentPage: _navigationController.currentPage,
                  onToggle: _drawerController.toggleLeftDrawer,
                  onPageChange: _navigationController.switchToPage,
                ),
              ),
            
            // Main content area
            Expanded(
              flex: (_drawerController.isRightDrawerOpen && isDesktop) ? 2 : 3,
              child: SafeArea(
                child: ListenableBuilder(
                  listenable: _navigationController,
                  builder: (context, _) => _buildMainContent(context, theme, accentColor),
                ),
              ),
            ),
            
            // Right drawer for thoughts and memory
            if (isDesktop)
              ListenableBuilder(
                listenable: _drawerController,
                builder: (context, _) {
                  if (!_drawerController.isRightDrawerOpen) return const SizedBox.shrink();
                  
                  return HomeRightDrawer(
                    accentColor: accentColor,
                    glowController: _glowAnimationController,
                    glowAnimation: _glowAnimation,
                    isExpanded: _drawerController.isRightDrawerExpanded,
                    onToggle: _drawerController.toggleRightDrawer,
                    scrollToMessageId: _drawerController.scrollToThoughtId,
                  );
                },
              ),
          ],
        ),
      ),
      floatingActionButton: isDesktop && !_drawerController.isRightDrawerOpen
          ? _buildRightDrawerButton(context, theme, accentColor)
          : null,
      floatingActionButtonLocation: FloatingActionButtonLocation.endTop,
    );
  }

  Widget _buildRightDrawerButton(BuildContext context, ThemeData theme, Color accentColor) {
    return Positioned(
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
          onPressed: () => _drawerController.setRightDrawerOpen(true),
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
    );
  }

  Widget _buildMainContent(BuildContext context, ThemeData theme, Color accentColor) {
    switch (_navigationController.currentPage) {
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
    final layoutState = ref.watch(layoutProvider);
    final isVoiceMode = layoutState.modality == ConversationModality.voice;
    
    return Padding(
      padding: EdgeInsets.only(
        left: 40,
        right: 40,
        top: isVoiceMode ? 0 : 20, // No top padding in voice mode
        bottom: isVoiceMode ? 0 : 20, // No bottom padding in voice mode
      ),
      child: ModalAwareLayout(
        avatar: AnimatedAvatarContainer(
          child: HomeAvatarHeader(
            accentColor: accentColor,
            glowController: _glowAnimationController,
            glowAnimation: _glowAnimation,
          ),
        ),
        messages: HomeConversationArea(
          scrollController: _conversationController,
          accentColor: accentColor,
          glowController: _glowAnimationController,
          glowAnimation: _glowAnimation,
          onFeedback: _handleFeedback,
          onCopy: _handleCopyToClipboard,
          onSave: _handleSaveToFile,
          onRemember: _handleRememberConversation,
        ),
        input: HomeInputArea(
          controller: _messageController,
          focusNode: _messageFocusNode,
          accentColor: accentColor,
          onSend: () => _sendMessage(_messageController.text),
          onVoice: () => ref.read(layoutProvider.notifier).toggleVoiceText(),
          sendButtonKey: _sendButtonKey,
          voiceButtonKey: _voiceButtonKey,
        ),
        onShowChat: () => ref.read(layoutProvider.notifier).switchModality(ConversationModality.text),
      ),
    );
  }

  // Message handling
  void _sendMessage(String text) async {
    // Switch to text mode when sending first message
    final conversationState = ref.read(conversationProvider);
    if (conversationState.messages.isEmpty) {
      ref.read(layoutProvider.notifier).switchModality(ConversationModality.text);
    }
    
    await HomeScreenHelpers.sendMessage(
      ref: ref,
      text: text,
      controller: _messageController,
      focusNode: _messageFocusNode,
      sendButtonKey: _sendButtonKey,
    );
  }

  // Feedback handling
  Future<void> _handleFeedback(String messageId, bool isPositive) async {
    final handler = ConversationFeedbackHandler(
      context: context,
      ref: ref,
      accentColor: Theme.of(context).colorScheme.primary,
    );
    await handler.handleFeedback(messageId, isPositive);
  }

  // Export handling
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

  // Memory handling
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
      
      // Create full conversation text
      final fullConversation = conversationState.messages
          .asMap()
          .entries
          .map((entry) {
            final speaker = entry.key.isOdd ? "AICO" : "You";
            return '$speaker: ${entry.value.content}';
          })
          .join('\n\n');
      
      // Save to Memory Album
      final memoryId = await ref.read(memoryAlbumProvider.notifier).rememberConversation(
        conversationId: conversationState.currentConversationId!,
        title: title,
        summary: fullConversation,
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
}
