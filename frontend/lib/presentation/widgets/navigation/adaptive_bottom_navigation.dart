import 'package:aico_frontend/core/constants/route_names.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Adaptive bottom navigation bar implementing AICO's hub-and-spoke navigation.
/// Features 4 primary sections with soft purple accent for active states.
class AdaptiveBottomNavigation extends StatelessWidget {
  final String currentRoute;

  const AdaptiveBottomNavigation({
    super.key,
    required this.currentRoute,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final currentIndex = _getCurrentIndex();

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        boxShadow: [
          BoxShadow(
            color: theme.shadowColor.withValues(alpha: 0.1),
            blurRadius: 8,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        child: Container(
          height: 80,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildNavItem(
                context,
                icon: Icons.home_outlined,
                activeIcon: Icons.home,
                label: 'Home',
                route: RouteNames.home,
                index: 0,
                isActive: currentIndex == 0,
              ),
              _buildNavItem(
                context,
                icon: Icons.chat_bubble_outline,
                activeIcon: Icons.chat_bubble,
                label: 'Conversation',
                route: RouteNames.conversation,
                index: 1,
                isActive: currentIndex == 1,
              ),
              // Space for floating voice button
              const SizedBox(width: 56),
              _buildNavItem(
                context,
                icon: Icons.people_outline,
                activeIcon: Icons.people,
                label: 'People',
                route: RouteNames.people,
                index: 2,
                isActive: currentIndex == 2,
              ),
              _buildNavItem(
                context,
                icon: Icons.more_horiz,
                activeIcon: Icons.more_horiz,
                label: 'More',
                route: RouteNames.more,
                index: 3,
                isActive: currentIndex == 3,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildNavItem(
    BuildContext context, {
    required IconData icon,
    required IconData activeIcon,
    required String label,
    required String route,
    required int index,
    required bool isActive,
  }) {
    final theme = Theme.of(context);
    final accentColor = const Color(0xFFB8A1EA); // Soft purple accent

    return Expanded(
      child: InkWell(
        onTap: () => context.go(route),
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                curve: Curves.easeOut,
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: isActive ? accentColor.withValues(alpha: 0.1) : Colors.transparent,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  isActive ? activeIcon : icon,
                  size: 24,
                  color: isActive ? accentColor : theme.colorScheme.onSurface.withValues(alpha: 0.6),
                ),
              ),
              const SizedBox(height: 4),
              AnimatedDefaultTextStyle(
                duration: const Duration(milliseconds: 200),
                style: theme.textTheme.labelSmall!.copyWith(
                  color: isActive ? accentColor : theme.colorScheme.onSurface.withValues(alpha: 0.6),
                  fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
                ),
                child: Text(label),
              ),
            ],
          ),
        ),
      ),
    );
  }

  int _getCurrentIndex() {
    final primarySection = RouteNames.getPrimarySection(currentRoute);
    switch (primarySection) {
      case RouteNames.home:
        return 0;
      case RouteNames.conversation:
        return 1;
      case RouteNames.people:
        return 2;
      case RouteNames.more:
        return 3;
      default:
        return 0;
    }
  }
}
