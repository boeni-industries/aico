import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/route_names.dart';

/// Adaptive sidebar navigation for desktop and tablet landscape layouts.
/// Features persistent avatar area with collapsible sections and soft purple accents.
class AdaptiveSidebarNavigation extends StatefulWidget {
  final String currentRoute;
  final bool isCollapsed;

  const AdaptiveSidebarNavigation({
    super.key,
    required this.currentRoute,
    this.isCollapsed = false,
  });

  @override
  State<AdaptiveSidebarNavigation> createState() => _AdaptiveSidebarNavigationState();
}

class _AdaptiveSidebarNavigationState extends State<AdaptiveSidebarNavigation> {
  late bool _isCollapsed;

  @override
  void initState() {
    super.initState();
    _isCollapsed = widget.isCollapsed;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final accentColor = const Color(0xFFB8A1EA); // Soft purple accent
    final sidebarWidth = _isCollapsed ? 80.0 : 280.0;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOut,
      width: sidebarWidth,
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          right: BorderSide(
            color: theme.dividerColor.withOpacity(0.1),
            width: 1,
          ),
        ),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          return Column(
            children: [
              _buildHeader(context, theme, accentColor),
              _buildAvatarSection(context, theme, accentColor),
              const SizedBox(height: 24),
              Expanded(
                child: _buildNavigationItems(context, theme, accentColor),
              ),
              _buildFooter(context, theme),
            ],
          );
        },
      ),
    );
  }

  Widget _buildHeader(BuildContext context, ThemeData theme, Color accentColor) {
    return Container(
      height: 64,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (!_isCollapsed) ...[
            Expanded(
              child: Text(
                'AICO',
                style: theme.textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: accentColor,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
          IconButton(
            onPressed: () {
              setState(() {
                _isCollapsed = !_isCollapsed;
              });
            },
            icon: Icon(
              _isCollapsed ? Icons.menu : Icons.menu_open,
              color: theme.colorScheme.onSurface.withOpacity(0.7),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAvatarSection(BuildContext context, ThemeData theme, Color accentColor) {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Avatar with mood ring
          Container(
            width: _isCollapsed ? 48 : 96,
            height: _isCollapsed ? 48 : 96,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(
                color: accentColor.withOpacity(0.3),
                width: 2,
              ),
            ),
            child: Container(
              margin: const EdgeInsets.all(4),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    accentColor.withOpacity(0.1),
                    accentColor.withOpacity(0.05),
                  ],
                ),
              ),
              child: Icon(
                Icons.face,
                size: _isCollapsed ? 24 : 48,
                color: accentColor,
              ),
            ),
          ),
          
          if (!_isCollapsed) ...[
            const SizedBox(height: 12),
            Text(
              'Feeling thoughtful',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.7),
              ),
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.green.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: const BoxDecoration(
                      color: Colors.green,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Flexible(
                    child: Text(
                      'Local',
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: Colors.green,
                        fontWeight: FontWeight.w500,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildNavigationItems(BuildContext context, ThemeData theme, Color accentColor) {
    return SingleChildScrollView(
      padding: EdgeInsets.symmetric(horizontal: _isCollapsed ? 2 : 12),
      child: Column(
        children: [
          _buildNavItem(
            context,
            theme,
            accentColor,
            icon: Icons.home_outlined,
            activeIcon: Icons.home,
            label: 'Home',
            route: RouteNames.home,
            isActive: RouteNames.isHomeRoute(widget.currentRoute),
          ),
          
          _buildNavItem(
            context,
            theme,
            accentColor,
            icon: Icons.auto_stories_outlined,
            activeIcon: Icons.auto_stories,
            label: _isCollapsed ? 'Memory' : 'Memory & Timeline',
            route: RouteNames.memory,
            isActive: widget.currentRoute.startsWith(RouteNames.memory),
          ),
          _buildNavItem(
            context,
            theme,
            accentColor,
            icon: Icons.admin_panel_settings_outlined,
            activeIcon: Icons.admin_panel_settings,
            label: 'Admin',
            route: RouteNames.admin,
            isActive: widget.currentRoute.startsWith(RouteNames.admin),
          ),
        ],
      ),
    );
  }

  Widget _buildNavItem(
    BuildContext context,
    ThemeData theme,
    Color accentColor, {
    required IconData icon,
    required IconData activeIcon,
    required String label,
    required String route,
    required bool isActive,
  }) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 2),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => context.go(route),
          borderRadius: BorderRadius.circular(12),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            padding: EdgeInsets.symmetric(
              horizontal: _isCollapsed ? 4 : 16, 
              vertical: 12
            ),
            decoration: BoxDecoration(
              color: isActive ? accentColor.withOpacity(0.1) : Colors.transparent,
              borderRadius: BorderRadius.circular(12),
            ),
            child: _isCollapsed
                ? Center(
                    child: Icon(
                      isActive ? activeIcon : icon,
                      size: 20,
                      color: isActive ? accentColor : theme.colorScheme.onSurface.withOpacity(0.7),
                    ),
                  )
                : Row(
                    children: [
                      Icon(
                        isActive ? activeIcon : icon,
                        size: 20,
                        color: isActive ? accentColor : theme.colorScheme.onSurface.withOpacity(0.7),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Text(
                          label,
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: isActive ? accentColor : theme.colorScheme.onSurface.withOpacity(0.8),
                            fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
                          ),
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

  Widget _buildFooter(BuildContext context, ThemeData theme) {
    return Container(
      padding: EdgeInsets.all(_isCollapsed ? 4 : 16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Settings at bottom following UX best practices - always visible
          _buildNavItem(
            context,
            theme,
            const Color(0xFFB8A1EA),
            icon: Icons.settings_outlined,
            activeIcon: Icons.settings,
            label: 'Settings',
            route: RouteNames.settings,
            isActive: widget.currentRoute.startsWith(RouteNames.settings),
          ),
        ],
      ),
    );
  }
}
