import 'package:flutter/material.dart';

/// Tab options for right drawer
enum DrawerTab {
  thinking,
  emotions,
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
      mainAxisSize: MainAxisSize.min,
      children: [
        _TabButton(
          label: 'Thinking',
          icon: Icons.psychology_outlined,
          isSelected: selectedTab == DrawerTab.thinking,
          onTap: () => onTabChanged(DrawerTab.thinking),
        ),
        const SizedBox(width: 8),
        _TabButton(
          label: 'Emotions',
          icon: Icons.favorite_outline,
          isSelected: selectedTab == DrawerTab.emotions,
          onTap: () => onTabChanged(DrawerTab.emotions),
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
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected
              ? Colors.white.withValues(alpha: 0.08)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 14,
              color: isSelected
                  ? Colors.white.withValues(alpha: 0.9)
                  : theme.colorScheme.onSurface.withValues(alpha: 0.4),
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: theme.textTheme.labelMedium?.copyWith(
                fontSize: 11,
                fontWeight: FontWeight.w500,
                color: isSelected
                    ? Colors.white.withValues(alpha: 0.9)
                    : theme.colorScheme.onSurface.withValues(alpha: 0.5),
                letterSpacing: 0.01,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
