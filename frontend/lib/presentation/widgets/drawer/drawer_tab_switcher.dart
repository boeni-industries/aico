import 'package:flutter/material.dart';

/// Tab options for right drawer
enum DrawerTab {
  thinking,
  emotions,
  notifications,
}

/// Glassmorphic tab switcher for right drawer
class DrawerTabSwitcher extends StatelessWidget {
  final DrawerTab selectedTab;
  final ValueChanged<DrawerTab> onTabChanged;

  const DrawerTabSwitcher({
    super.key,
    required this.selectedTab,
    required this.onTabChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _TabButton(
            label: 'Thinking',
            icon: Icons.psychology_outlined,
            isSelected: selectedTab == DrawerTab.thinking,
            onTap: () => onTabChanged(DrawerTab.thinking),
          ),
        ),
        const SizedBox(width: 6),
        Expanded(
          child: _TabButton(
            label: 'Emotions',
            icon: Icons.favorite_outline,
            isSelected: selectedTab == DrawerTab.emotions,
            onTap: () => onTabChanged(DrawerTab.emotions),
          ),
        ),
        const SizedBox(width: 6),
        Expanded(
          child: _TabButton(
            label: 'Notify',
            icon: Icons.chat_bubble_outline,
            isSelected: selectedTab == DrawerTab.notifications,
            onTap: () => onTabChanged(DrawerTab.notifications),
          ),
        ),
      ],
    );
  }
}

class _TabButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool isSelected;
  final VoidCallback onTap;

  const _TabButton({
    required this.label,
    required this.icon,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeInOutCubic,
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected
              ? Colors.white.withValues(alpha: 0.08)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon,
              size: 14,
              color: isSelected
                  ? Colors.white.withValues(alpha: 0.9)
                  : theme.colorScheme.onSurface.withValues(alpha: 0.4),
            ),
            const SizedBox(width: 4),
            Flexible(
              child: Text(
                label,
                style: theme.textTheme.labelMedium?.copyWith(
                  fontSize: 10,
                  fontWeight: FontWeight.w500,
                  color: isSelected
                      ? Colors.white.withValues(alpha: 0.9)
                      : theme.colorScheme.onSurface.withValues(alpha: 0.5),
                  letterSpacing: 0.01,
                ),
                overflow: TextOverflow.ellipsis,
                maxLines: 1,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
