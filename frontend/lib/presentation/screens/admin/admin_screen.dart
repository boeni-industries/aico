import 'package:aico_frontend/core/logging/providers/logging_providers.dart';
import 'package:aico_frontend/core/logging/services/aico_logger.dart';
import 'package:aico_frontend/presentation/screens/admin/encryption_test_screen.dart';
import 'package:aico_frontend/presentation/widgets/chat/thinking_bubble.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Admin screen for system administration and developer tools.
/// Uses main content area following three-pane layout design principles.
class AdminScreen extends StatefulWidget {
  const AdminScreen({super.key});

  @override
  State<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends State<AdminScreen> with TickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Column(
      children: [
        // Admin header
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            border: Border(
              bottom: BorderSide(
                color: theme.dividerColor.withValues(alpha: 0.1),
              ),
            ),
          ),
          child: Row(
            children: [
              Icon(
                Icons.admin_panel_settings,
                size: 32,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(width: 16),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Admin & Developer Tools',
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Text(
                    'System administration and diagnostic utilities',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),

        // Main navigation tabs
        Container(
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            border: Border(
              bottom: BorderSide(
                color: theme.dividerColor.withValues(alpha: 0.1),
              ),
            ),
          ),
          child: TabBar(
            controller: _tabController,
            labelColor: theme.colorScheme.primary,
            unselectedLabelColor: theme.colorScheme.onSurface.withValues(alpha: 0.7),
            indicatorColor: theme.colorScheme.primary,
            tabs: const [
              Tab(text: 'Dashboard'),
              Tab(text: 'User Management'),
              Tab(text: 'System Settings'),
              Tab(text: 'Developer Tools'),
            ],
          ),
        ),

        // Tab content
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildDashboard(context, theme),
              _buildUserManagement(context, theme),
              _buildSystemSettings(context, theme),
              _buildDeveloperTools(context, theme),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildDashboard(BuildContext context, ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Admin Dashboard',
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'System overview and key metrics will be displayed here.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildUserManagement(BuildContext context, ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'User Management',
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'User management features will be implemented here.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSystemSettings(BuildContext context, ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'System Settings',
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'System configuration options will be available here.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDeveloperTools(BuildContext context, ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: SingleChildScrollView(
        child: Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            _buildDeveloperToolCard(
              context,
              theme,
              'Thinking Bubble Test',
              'Preview particle formation animation',
              Icons.auto_awesome,
              () => _showThinkingBubbleTest(context),
            ),
            _buildDeveloperToolCard(
              context,
              theme,
              'Encryption Test',
              'Test transport encryption and key exchange',
              Icons.security,
              () => _showEncryptionTest(context),
            ),
            _buildDeveloperToolCard(
              context,
              theme,
              'API Testing',
              'Test API endpoints and monitor responses',
              Icons.api,
              () => _showApiTesting(context),
            ),
            _buildDeveloperToolCard(
              context,
              theme,
              'System Diagnostics',
              'Monitor system health and performance',
              Icons.monitor_heart,
              () => _showDiagnostics(context),
            ),
            _buildDeveloperToolCard(
              context,
              theme,
              'Application Logs',
              'View and analyze debug information',
              Icons.bug_report,
              () => _showLogs(context),
            ),
            Consumer(
              builder: (context, ref, _) {
                final AsyncValue<AICOLogger> loggerAsync = ref.watch(aicoLoggerProvider);
                
                return loggerAsync.when(
                  data: (logger) => _buildDeveloperToolCard(
                    context,
                    theme,
                    'Send Test Log',
                    'Trigger a test log entry at the backend',
                    Icons.send,
                    () => _sendTestLog(context, logger),
                    enabled: true,
                    loading: false,
                  ),
                  loading: () => _buildDeveloperToolCard(
                    context,
                    theme,
                    'Send Test Log',
                    'Trigger a test log entry at the backend',
                    Icons.send,
                    null,
                    enabled: false,
                    loading: true,
                  ),
                  error: (error, stack) => _buildDeveloperToolCard(
                    context,
                    theme,
                    'Send Test Log',
                    'Logger initialization failed',
                    Icons.send,
                    null,
                    enabled: false,
                    loading: false,
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  // Method to show thinking bubble test in a dialog
  void _showThinkingBubbleTest(BuildContext context) {
    final theme = Theme.of(context);
    
    showDialog(
      context: context,
      builder: (context) => Dialog(
        backgroundColor: theme.colorScheme.surface,
        child: Container(
          width: 600,
          height: 400,
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Thinking Bubble Animation Test',
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              const SizedBox(height: 32),
              const Expanded(
                child: Center(
                  child: _ThinkingBubbleDemo(),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // Method to show encryption test in a dialog
  void _showEncryptionTest(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          width: 800,
          height: 600,
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Encryption Test',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const Expanded(child: EncryptionTestScreen()),
            ],
          ),
        ),
      ),
    );
  }

  // Method to show API testing placeholder
  void _showApiTesting(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('API Testing'),
        content: const Text('API testing tools will be implemented here.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  // Method to show diagnostics placeholder
  void _showDiagnostics(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('System Diagnostics'),
        content: const Text('System diagnostic tools will be implemented here.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  // Method to send a test log entry to the backend
  Future<void> _sendTestLog(BuildContext context, AICOLogger logger) async {
    try {
      AICOLogger.info(
        'Test log entry from Developer Tools',
        topic: 'devtools/test/send',
        extra: {'source': 'SendTestLogCard', 'timestamp': DateTime.now().toIso8601String()},
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Test log entry sent!')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to send test log: $e')),
        );
      }
    }
  }

  // Method to show logs placeholder
  void _showLogs(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Application Logs'),
        content: const Text('Log viewer will be implemented here.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  Widget _buildDeveloperToolCard(
    BuildContext context,
    ThemeData theme,
    String title,
    String description,
    IconData icon,
    VoidCallback? onTap, {
    bool enabled = true,
    bool loading = false,
  }) {
    return SizedBox(
      width: 280,
      height: 140,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: enabled ? onTap : null,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: theme.colorScheme.surfaceContainerLow,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: theme.colorScheme.outline.withValues(alpha: 0.2),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  icon,
                  size: 28,
                  color: enabled ? theme.colorScheme.primary : theme.disabledColor,
                ),
                const SizedBox(height: 8),
                Text(
                  title,
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                    color: enabled ? null : theme.disabledColor,
                  ),
                ),
                const SizedBox(height: 4),
                Expanded(
                  child: loading
                      ? Center(child: CircularProgressIndicator(strokeWidth: 2))
                      : Text(
                          description,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Demo widget that shows thinking bubble transitioning to text
class _ThinkingBubbleDemo extends StatefulWidget {
  const _ThinkingBubbleDemo();

  @override
  State<_ThinkingBubbleDemo> createState() => _ThinkingBubbleDemoState();
}

class _ThinkingBubbleDemoState extends State<_ThinkingBubbleDemo> 
    with SingleTickerProviderStateMixin {
  bool _showText = false;
  String _displayText = '';
  final String _fullText = 'Let me help you with that! I can assist with various tasks and answer your questions.';
  late AnimationController _fadeController;
  late Animation<double> _bubbleFadeOut;
  late Animation<double> _textFadeIn;
  
  @override
  void initState() {
    super.initState();
    
    _fadeController = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    );
    
    // Bubble fades out in first half
    _bubbleFadeOut = Tween<double>(begin: 1.0, end: 0.0).animate(
      CurvedAnimation(
        parent: _fadeController,
        curve: const Interval(0.0, 0.5, curve: Curves.easeOut),
      ),
    );
    
    // Text fades in during second half
    _textFadeIn = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _fadeController,
        curve: const Interval(0.5, 1.0, curve: Curves.easeIn),
      ),
    );
    
    // Show thinking bubble for 3 seconds, then smooth transition
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) {
        setState(() => _showText = true);
        _fadeController.forward().then((_) {
          if (mounted) _streamText();
        });
      }
    });
  }
  
  @override
  void dispose() {
    _fadeController.dispose();
    super.dispose();
  }
  
  void _streamText() async {
    for (int i = 0; i < _fullText.length; i++) {
      if (!mounted) break;
      await Future.delayed(const Duration(milliseconds: 30));
      if (mounted) {
        setState(() {
          _displayText = _fullText.substring(0, i + 1);
        });
      }
    }
  }
  
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 400),
          child: Text(
            _showText 
              ? 'Text streams in smoothly...' 
              : 'Particles converge where text will appear',
            key: ValueKey(_showText),
            style: theme.textTheme.bodyLarge?.copyWith(
              fontWeight: FontWeight.w500,
              color: theme.colorScheme.onSurface.withOpacity(0.7),
            ),
          ),
        ),
        const SizedBox(height: 32),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            CircleAvatar(
              radius: 16,
              backgroundColor: const Color(0xFFB8A1EA).withOpacity(0.1),
              child: const Icon(
                Icons.face,
                size: 16,
                color: Color(0xFFB8A1EA),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: AnimatedBuilder(
                animation: _fadeController,
                builder: (context, child) {
                  return Stack(
                    alignment: Alignment.topLeft,
                    children: [
                      // Thinking bubble fading out - fixed height
                      if (!_showText || _bubbleFadeOut.value > 0)
                        Opacity(
                          opacity: _bubbleFadeOut.value,
                          child: const SizedBox(
                            height: 72,
                            child: ThinkingBubble(),
                          ),
                        ),
                      
                      // Text bubble fading in - can expand
                      if (_showText && _textFadeIn.value > 0)
                        Opacity(
                          opacity: _textFadeIn.value,
                          child: Container(
                            constraints: const BoxConstraints(
                              minHeight: 72,
                              maxHeight: 200, // Allow expansion up to 200px
                            ),
                            width: double.infinity,
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: theme.colorScheme.surface,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(
                                color: theme.dividerColor.withOpacity(0.1),
                                width: 1,
                              ),
                            ),
                            child: SingleChildScrollView(
                              child: Text(
                                _displayText,
                                style: theme.textTheme.bodyMedium,
                              ),
                            ),
                          ),
                        ),
                    ],
                  );
                },
              ),
            ),
            const SizedBox(width: 48),
          ],
        ),
      ],
    );
  }
}
