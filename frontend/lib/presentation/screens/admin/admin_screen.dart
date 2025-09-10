import 'package:aico_frontend/presentation/screens/admin/encryption_test_screen.dart';
import 'package:aico_frontend/core/logging/services/aico_logger.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aico_frontend/core/logging/providers/logging_providers.dart';

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
