import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/route_names.dart';

/// More screen implementing progressive disclosure hub.
/// Organizes memory, settings, and admin features by usage frequency.
class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final accentColor = const Color(0xFFB8A1EA); // Soft purple accent

    return Scaffold(
      appBar: AppBar(
        title: const Text('More'),
        backgroundColor: theme.colorScheme.surface,
        elevation: 0,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Memory & Timeline section
          _buildSectionHeader(context, 'Memory & Timeline'),
          _buildMenuItem(
            context,
            theme,
            accentColor,
            icon: Icons.auto_stories_outlined,
            title: 'Memory Timeline',
            subtitle: 'View your shared experiences and memories',
            onTap: () => context.go(RouteNames.memory),
          ),
          _buildMenuItem(
            context,
            theme,
            accentColor,
            icon: Icons.search,
            title: 'Search Memories',
            subtitle: 'Find specific conversations and moments',
            onTap: () => context.go(RouteNames.memorySearch),
          ),
          
          const SizedBox(height: 24),
          
          // Settings section
          _buildSectionHeader(context, 'Settings'),
          _buildMenuItem(
            context,
            theme,
            accentColor,
            icon: Icons.palette_outlined,
            title: 'Appearance & Theme',
            subtitle: 'Customize your AICO experience',
            onTap: () => context.go(RouteNames.settings),
          ),
          _buildMenuItem(
            context,
            theme,
            accentColor,
            icon: Icons.privacy_tip_outlined,
            title: 'Privacy Controls',
            subtitle: 'Manage your data and privacy settings',
            onTap: () => context.go(RouteNames.privacySettings),
          ),
          
          const SizedBox(height: 24),
          
          // Admin section
          _buildSectionHeader(context, 'Advanced'),
          _buildMenuItem(
            context,
            theme,
            accentColor,
            icon: Icons.admin_panel_settings_outlined,
            title: 'System Administration',
            subtitle: 'Developer tools and system management',
            onTap: () => context.go(RouteNames.admin),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(BuildContext context, String title) {
    final theme = Theme.of(context);
    
    return Padding(
      padding: const EdgeInsets.only(bottom: 12, left: 4),
      child: Text(
        title,
        style: theme.textTheme.titleMedium?.copyWith(
          fontWeight: FontWeight.w600,
          color: theme.colorScheme.onSurface.withValues(alpha: 0.8),
        ),
      ),
    );
  }

  Widget _buildMenuItem(
    BuildContext context,
    ThemeData theme,
    Color accentColor, {
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: theme.colorScheme.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: theme.dividerColor.withValues(alpha: 0.1),
                width: 1,
              ),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: accentColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(
                    icon,
                    size: 24,
                    color: accentColor,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: theme.textTheme.bodyLarge?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        subtitle,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                        ),
                      ),
                    ],
                  ),
                ),
                Icon(
                  Icons.chevron_right,
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
