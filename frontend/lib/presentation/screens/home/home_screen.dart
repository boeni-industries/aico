import 'package:aico_frontend/presentation/providers/theme_provider.dart';
import 'package:aico_frontend/presentation/models/conversation_message.dart';
import 'package:aico_frontend/presentation/providers/auth_provider.dart';
import 'package:aico_frontend/presentation/providers/conversation_provider.dart';
import 'package:aico_frontend/presentation/screens/admin/admin_screen.dart';
import 'package:aico_frontend/presentation/screens/memory/memory_screen.dart';
import 'package:aico_frontend/presentation/screens/settings/settings_screen.dart';
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

  @override
  void initState() {
    super.initState();
    // Theme management now handled via Riverpod providers
    
    // Listen for conversation changes to auto-scroll
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.listenManual(conversationProvider, (previous, next) {
        // Auto-scroll when new messages are added
        if (previous != null && next.messages.length > previous.messages.length) {
          _scrollToBottom();
        }
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final accentColor = const Color(0xFFB8A1EA); // Soft purple accent
    final screenWidth = MediaQuery.of(context).size.width;
    final isDesktop = screenWidth > 800;
    
    return Scaffold(
      body: Stack(
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
      ),
      // Theme/contrast toolbar and drawer toggles
      floatingActionButton: Stack(
        children: [
          
          // Right side controls (theme/logout buttons) - positioned relative to right drawer
          Positioned(
            right: _isRightDrawerOpen 
                ? (_isRightDrawerExpanded ? 300 : 72) // Equal spacing from drawer edge
                : 16, // 16px from screen edge when drawer is closed
            top: 16,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                // Minimal theme toolbar
                Container(
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surface,
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(
                      color: theme.dividerColor.withValues(alpha: 0.2),
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Consumer(
                        builder: (context, ref, child) {
                          final themeState = ref.watch(themeControllerProvider);
                          return IconButton(
                            onPressed: () async {
                              debugPrint('Theme toggle pressed');
                              await ref.read(themeControllerProvider.notifier).toggleTheme();
                              debugPrint('Theme toggled');
                            },
                            icon: Icon(themeState.themeMode == ThemeMode.light ? Icons.wb_sunny : Icons.nightlight_round),
                            tooltip: 'Toggle theme',
                            style: IconButton.styleFrom(
                              foregroundColor: theme.colorScheme.onSurface,
                            ),
                          );
                        },
                      ),
                      IconButton(
                        onPressed: () async {
                          debugPrint('Contrast toggle pressed');
                          final currentState = ref.read(themeControllerProvider);
                          await ref.read(themeControllerProvider.notifier).setHighContrastEnabled(!currentState.isHighContrast);
                          debugPrint('High contrast toggled to: ${!currentState.isHighContrast}');
                        },
                        icon: Consumer(
                          builder: (context, ref, child) {
                            final themeState = ref.watch(themeControllerProvider);
                            return Icon(
                              Icons.contrast,
                              color: themeState.isHighContrast 
                                  ? theme.colorScheme.primary 
                                  : theme.colorScheme.onSurface,
                            );
                          },
                        ),
                        tooltip: 'Toggle high contrast',
                        style: IconButton.styleFrom(
                          foregroundColor: theme.colorScheme.onSurface,
                        ),
                      ),
                      IconButton(
                        onPressed: () {
                          ref.read(authProvider.notifier).logout();
                        },
                        icon: const Icon(Icons.logout),
                        tooltip: 'Logout',
                        style: IconButton.styleFrom(
                          foregroundColor: theme.colorScheme.onSurface,
                        ),
                      ),
                    ],
                  ),
                ),
                
                const SizedBox(height: 8),
                
              ],
            ),
          ),
          
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
    );
  }

  Widget _buildAvatarHeader(BuildContext context, ThemeData theme, Color accentColor) {
    return Container(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          // Avatar with mood ring
          SizedBox(
            width: 96,
            child: Container(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: accentColor,
                  width: 3,
                ),
              ),
              child: CircleAvatar(
                radius: 60,
                backgroundColor: theme.colorScheme.surface,
                child: Icon(
                  Icons.face,
                  size: 48,
                  color: accentColor,
                ),
              ),
            ),
          ),
          
          const SizedBox(height: 12),
          
          // Emotional state
          Text(
            'Feeling curious and ready to chat',
            style: theme.textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w500,
            ),
          ),
          
          const SizedBox(height: 8),
          
          // System status
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.green.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 6,
                  height: 6,
                  decoration: const BoxDecoration(
                    color: Colors.green,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 6),
                const Text(
                  'Local & Secure',
                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.w500),
                ),
              ],
            ),
          ),
        ],
      ),
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
    );
  }

  Widget _buildMessageBubble(BuildContext context, ThemeData theme, Color accentColor, ConversationMessage message) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (message.isFromAico) ...[
            CircleAvatar(
              radius: 16,
              backgroundColor: accentColor.withValues(alpha: 0.1),
              child: Icon(Icons.face, size: 16, color: accentColor),
            ),
            const SizedBox(width: 12),
          ],
          Expanded(
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: message.isFromAico 
                    ? theme.colorScheme.surface
                    : accentColor.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(16),
                border: message.isFromAico 
                    ? Border.all(color: theme.dividerColor.withValues(alpha: 0.1))
                    : null,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    message.message,
                    style: theme.textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _formatTimestamp(message.timestamp),
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (!message.isFromAico) const SizedBox(width: 48),
        ],
      ),
    );
  }

  Widget _buildInputArea(BuildContext context, ThemeData theme, Color accentColor) {
    return Container(
      padding: const EdgeInsets.all(24),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: theme.dividerColor.withValues(alpha: 0.1)),
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
    );
  }

  Widget _buildRightDrawer(BuildContext context, ThemeData theme, Color accentColor) {
    return Container(
      width: _isRightDrawerExpanded ? 300 : 72,
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          left: BorderSide(color: theme.dividerColor.withValues(alpha: 0.1)),
        ),
      ),
      child: SafeArea(
        child: Column(
          children: [
            // Drawer header
            if (_isRightDrawerExpanded)
              Container(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Text(
                      'AICO\'s Thoughts',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const Spacer(),
                  ],
                ),
              ),
            
            // Thoughts section
            Expanded(
              child: _isRightDrawerExpanded
                  ? ListView(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      children: [
                        _buildThoughtCard(context, theme, accentColor,
                          type: 'Suggestion',
                          message: 'Maybe we could try that meditation exercise you mentioned last week?',
                        ),
                        const SizedBox(height: 12),
                        _buildThoughtCard(context, theme, accentColor,
                          type: 'Reminder',
                          message: 'Your sister\'s birthday is coming up next week. Want to plan something special?',
                        ),
                        const SizedBox(height: 12),
                        _buildThoughtCard(context, theme, accentColor,
                          type: 'Memory',
                          message: 'Remember when we talked about your dream trip to Japan? I found some interesting places you might like.',
                        ),
                        
                        const SizedBox(height: 24),
                        
                        // Memory timeline section
                        Text(
                          'Our Journey',
                          style: theme.textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 12),
                        
                        _buildMemoryItem(context, theme, accentColor,
                          title: 'Deep conversation about career goals',
                          time: 'Yesterday, 8:30 PM',
                        ),
                        _buildMemoryItem(context, theme, accentColor,
                          title: 'Shared funny story about weekend',
                          time: '2 days ago',
                        ),
                        _buildMemoryItem(context, theme, accentColor,
                          title: 'Helped plan family dinner',
                          time: '1 week ago',
                        ),
                        _buildMemoryItem(context, theme, accentColor,
                          title: 'First conversation together',
                          time: '2 weeks ago',
                        ),
                      ],
                    )
                  : const SizedBox.shrink(),
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


  void _sendMessage(String text) {
    if (text.trim().isEmpty) return;
    
    // Clear the input field immediately
    _messageController.clear();
    
    // Send message through conversation provider
    ref.read(conversationProvider.notifier).sendMessage(text.trim());
    
    // Scroll to bottom after sending
    _scrollToBottom();
    
    // Refocus the input field for continuous conversation
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _messageFocusNode.requestFocus();
    });
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_conversationController.hasClients) {
        _conversationController.animateTo(
          _conversationController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  String _formatTimestamp(DateTime timestamp) {
    // Convert UTC timestamp to local time
    final localTimestamp = timestamp.toLocal();
    final now = DateTime.now();
    final diff = now.difference(localTimestamp);
    
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes} minutes ago';
    if (diff.inHours < 24) return '${diff.inHours} hours ago';
    return '${diff.inDays} days ago';
  }

  Widget _buildLeftDrawer(BuildContext context, ThemeData theme, Color accentColor) {
    return Container(
      width: _isLeftDrawerExpanded ? 240 : 72,
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          right: BorderSide(color: theme.dividerColor.withValues(alpha: 0.1)),
        ),
      ),
      child: SafeArea(
        child: Column(
          children: [
            // Navigation items with toggle as first item
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

  @override
  void dispose() {
    _messageController.dispose();
    _conversationController.dispose();
    _messageFocusNode.dispose();
    super.dispose();
  }
}

