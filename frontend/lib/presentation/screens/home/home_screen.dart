import 'package:flutter/material.dart';
import '../../../core/di/service_locator.dart';
import '../../../core/theme/theme_manager.dart';

/// Home screen featuring avatar-centric hub with integrated conversation interface.
/// Serves as the primary interaction point with AICO, including conversation history
/// and collapsible right drawer for thoughts and memory timeline.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _isRightDrawerOpen = false;
  ThemeManager? _themeManager;
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _conversationController = ScrollController();
  final List<ConversationMessage> _messages = [
    ConversationMessage(
      isFromAico: true,
      message: "I noticed you seemed a bit stressed earlier. How are you feeling now? I'm here if you'd like to talk about anything.",
      timestamp: DateTime.now().subtract(const Duration(minutes: 5)),
    ),
  ];

  @override
  void initState() {
    super.initState();
    _themeManager = ServiceLocator.get<ThemeManager>();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final accentColor = const Color(0xFFB8A1EA); // Soft purple accent
    final screenWidth = MediaQuery.of(context).size.width;
    final isDesktop = screenWidth > 800;
    
    return Scaffold(
      body: Row(
        children: [
          // Main conversation area
          Expanded(
            flex: _isRightDrawerOpen && isDesktop ? 2 : 3,
            child: SafeArea(
              child: Column(
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
              ),
            ),
          ),
          
          // Right drawer for thoughts and memory
          if (_isRightDrawerOpen && isDesktop)
            _buildRightDrawer(context, theme, accentColor),
        ],
      ),
      // Theme/contrast toolbar and drawer toggle
      floatingActionButton: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          // Minimal theme toolbar
          Container(
            decoration: BoxDecoration(
              color: theme.colorScheme.surface,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(
                color: theme.dividerColor.withOpacity(0.2),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                IconButton(
                  onPressed: () {
                    _themeManager?.toggleTheme();
                  },
                  icon: Icon(_themeManager?.currentBrightness == Brightness.light ? Icons.wb_sunny : Icons.nightlight_round),
                  tooltip: _themeManager?.currentBrightness == Brightness.light ? 'Switch to dark mode' : 'Switch to light mode',
                  style: IconButton.styleFrom(
                    foregroundColor: theme.colorScheme.onSurface,
                  ),
                ),
                IconButton(
                  onPressed: () {
                    _themeManager?.setHighContrastEnabled(!(_themeManager?.isHighContrastEnabled ?? false));
                  },
                  icon: Icon(
                    Icons.contrast,
                    color: (_themeManager?.isHighContrastEnabled ?? false) ? Colors.orange : theme.colorScheme.onSurface,
                  ),
                  tooltip: (_themeManager?.isHighContrastEnabled ?? false) ? 'Disable high contrast' : 'Enable high contrast',
                  style: IconButton.styleFrom(
                    foregroundColor: theme.colorScheme.onSurface,
                  ),
                ),
              ],
            ),
          ),
          
          const SizedBox(height: 8),
          
          // Persistent drawer toggle
          if (isDesktop)
            Container(
              decoration: BoxDecoration(
                color: theme.colorScheme.surface,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: theme.dividerColor.withOpacity(0.2),
                ),
              ),
              child: IconButton(
                onPressed: () => setState(() => _isRightDrawerOpen = !_isRightDrawerOpen),
                icon: Icon(_isRightDrawerOpen ? Icons.chevron_right : Icons.chevron_left),
                tooltip: _isRightDrawerOpen ? 'Hide AICO\'s thoughts' : 'Show AICO\'s thoughts',
                style: IconButton.styleFrom(
                  foregroundColor: theme.colorScheme.onSurface,
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
          Container(
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
              color: Colors.green.withOpacity(0.1),
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
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 24),
      child: ListView.builder(
        controller: _conversationController,
        itemCount: _messages.length,
        itemBuilder: (context, index) {
          final message = _messages[index];
          return _buildMessageBubble(context, theme, accentColor, message);
        },
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
              backgroundColor: accentColor.withOpacity(0.1),
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
                    : accentColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(16),
                border: message.isFromAico 
                    ? Border.all(color: theme.dividerColor.withOpacity(0.1))
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
                      color: theme.colorScheme.onSurface.withOpacity(0.6),
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
          border: Border.all(color: theme.dividerColor.withOpacity(0.1)),
        ),
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: _messageController,
                decoration: InputDecoration(
                  hintText: 'Share what\'s on your mind...',
                  border: InputBorder.none,
                  hintStyle: TextStyle(
                    color: theme.colorScheme.onSurface.withOpacity(0.6),
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
                    backgroundColor: accentColor.withOpacity(0.1),
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
      width: 320,
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          left: BorderSide(color: theme.dividerColor.withOpacity(0.1)),
        ),
      ),
      child: SafeArea(
        child: Column(
          children: [
            // Drawer header
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
                  IconButton(
                    onPressed: () => setState(() => _isRightDrawerOpen = false),
                    icon: const Icon(Icons.close, size: 20),
                  ),
                ],
              ),
            ),
            
            // Thoughts section
            Expanded(
              child: ListView(
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
        color: accentColor.withOpacity(0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: accentColor.withOpacity(0.2)),
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
              Icon(Icons.close, size: 14, color: theme.colorScheme.onSurface.withOpacity(0.4)),
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
        border: Border.all(color: theme.dividerColor.withOpacity(0.1)),
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
              color: theme.colorScheme.onSurface.withOpacity(0.6),
            ),
          ),
        ],
      ),
    );
  }


  void _sendMessage(String text) {
    if (text.trim().isEmpty) return;
    
    setState(() {
      _messages.add(ConversationMessage(
        isFromAico: false,
        message: text.trim(),
        timestamp: DateTime.now(),
      ));
      _messageController.clear();
    });
    
    // Scroll to bottom
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _conversationController.animateTo(
        _conversationController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    });
    
    // Simulate AICO response
    Future.delayed(const Duration(seconds: 1), () {
      setState(() {
        _messages.add(ConversationMessage(
          isFromAico: true,
          message: "I understand. Thank you for sharing that with me. How can I help you with this?",
          timestamp: DateTime.now(),
        ));
      });
      
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _conversationController.animateTo(
          _conversationController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      });
    });
  }

  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final diff = now.difference(timestamp);
    
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes} minutes ago';
    if (diff.inHours < 24) return '${diff.inHours} hours ago';
    return '${diff.inDays} days ago';
  }

  @override
  void dispose() {
    _messageController.dispose();
    _conversationController.dispose();
    super.dispose();
  }
}

class ConversationMessage {
  final bool isFromAico;
  final String message;
  final DateTime timestamp;

  ConversationMessage({
    required this.isFromAico,
    required this.message,
    required this.timestamp,
  });
}
