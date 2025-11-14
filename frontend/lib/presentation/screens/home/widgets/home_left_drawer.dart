import 'dart:ui';

import 'package:aico_frontend/presentation/providers/auth_provider.dart';
import 'package:aico_frontend/presentation/providers/theme_provider.dart';
import 'package:aico_frontend/presentation/theme/glassmorphism.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// Forward declaration - NavigationPage enum is defined in home_screen.dart
// This is a workaround to avoid circular dependencies
enum NavigationPage {
  home,
  memory,
  admin,
  settings,
}

/// Left navigation drawer with collapsible menu
class HomeLeftDrawer extends ConsumerWidget {
  final Color accentColor;
  final bool isExpanded;
  final NavigationPage currentPage;
  final VoidCallback onToggle;
  final Function(NavigationPage) onPageChange;

  const HomeLeftDrawer({
    super.key,
    required this.accentColor,
    required this.isExpanded,
    required this.currentPage,
    required this.onToggle,
    required this.onPageChange,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
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
            width: isExpanded ? 240 : 72,
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
                  // Main navigation
                  Expanded(
                    child: ListView(
                      padding: EdgeInsets.symmetric(
                        horizontal: isExpanded ? 16 : 8,
                        vertical: 8,
                      ),
                      children: [
                        _buildToggleItem(theme),
                        const SizedBox(height: 8),
                        _buildNavItem(
                          theme,
                          Icons.home,
                          'Home',
                          currentPage == NavigationPage.home,
                          () => onPageChange(NavigationPage.home),
                        ),
                        const SizedBox(height: 8),
                        _buildNavItem(
                          theme,
                          Icons.auto_stories,
                          'Memory',
                          currentPage == NavigationPage.memory,
                          () => onPageChange(NavigationPage.memory),
                        ),
                        _buildNavItem(
                          theme,
                          Icons.admin_panel_settings,
                          'Admin',
                          currentPage == NavigationPage.admin,
                          () => onPageChange(NavigationPage.admin),
                        ),
                        _buildNavItem(
                          theme,
                          Icons.settings,
                          'Settings',
                          currentPage == NavigationPage.settings,
                          () => onPageChange(NavigationPage.settings),
                        ),
                      ],
                    ),
                  ),

                  // System controls
                  Container(
                    padding: EdgeInsets.symmetric(
                      horizontal: isExpanded ? 16 : 8,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      border: Border(
                        top: BorderSide(color: theme.dividerColor),
                      ),
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _buildSystemControl(
                          context,
                          ref,
                          theme,
                          () async {
                            final currentState = ref.read(themeControllerProvider);
                            await ref
                                .read(themeControllerProvider.notifier)
                                .setHighContrastEnabled(!currentState.isHighContrast);
                          },
                          'Contrast',
                          Icons.contrast,
                        ),
                        const SizedBox(height: 4),
                        _buildSystemControl(
                          context,
                          ref,
                          theme,
                          () {
                            ref.read(authProvider.notifier).logout();
                          },
                          'Logout',
                          Icons.logout,
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

  Widget _buildToggleItem(ThemeData theme) {
    if (!isExpanded) {
      return Container(
        margin: const EdgeInsets.only(bottom: 8),
        child: IconButton(
          onPressed: onToggle,
          icon: Icon(
            Icons.menu,
            color: accentColor.withValues(alpha: 0.6),
            size: 20,
          ),
          tooltip: 'Expand menu',
          style: IconButton.styleFrom(padding: EdgeInsets.zero),
        ),
      );
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          IconButton(
            onPressed: onToggle,
            icon: Icon(
              Icons.menu_open,
              color: accentColor.withValues(alpha: 0.6),
              size: 20,
            ),
            tooltip: 'Collapse menu',
            style: IconButton.styleFrom(padding: EdgeInsets.zero),
          ),
        ],
      ),
    );
  }

  Widget _buildNavItem(
    ThemeData theme,
    IconData icon,
    String title,
    bool isActive,
    VoidCallback onTap,
  ) {
    if (!isExpanded) {
      return Container(
        margin: const EdgeInsets.only(bottom: 4),
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
                  color: isActive
                      ? accentColor.withValues(alpha: 0.15)
                      : Colors.transparent,
                ),
                child: Icon(
                  icon,
                  color: isActive
                      ? accentColor
                      : theme.colorScheme.onSurface.withValues(alpha: 0.7),
                  size: 20,
                ),
              ),
            ),
          ),
        ),
      );
    }

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
              color: isActive
                  ? accentColor.withValues(alpha: 0.15)
                  : Colors.transparent,
            ),
            child: Row(
              children: [
                Icon(
                  icon,
                  color: isActive
                      ? accentColor
                      : theme.colorScheme.onSurface.withValues(alpha: 0.7),
                  size: 20,
                ),
                const SizedBox(width: 12),
                Text(
                  title,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: isActive
                        ? accentColor
                        : theme.colorScheme.onSurface.withValues(alpha: 0.7),
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

  Widget _buildSystemControl(
    BuildContext context,
    WidgetRef ref,
    ThemeData theme,
    VoidCallback onTap,
    String tooltip,
    IconData icon,
  ) {
    if (!isExpanded) {
      return Container(
        margin: const EdgeInsets.only(bottom: 4),
        child: Tooltip(
          message: tooltip,
          child: IconButton(
            onPressed: onTap,
            icon: Icon(
              icon,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
              size: 20,
            ),
            style: IconButton.styleFrom(padding: EdgeInsets.zero),
          ),
        ),
      );
    }

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
                Icon(
                  icon,
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
                  size: 20,
                ),
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
}
