import 'package:aico_frontend/presentation/theme/glassmorphism.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Conversation toolbar that slides out from under conversation container
/// Provides quick actions: copy to clipboard, save to file, remember this
class HomeToolbar extends StatelessWidget {
  final bool isVisible;
  final bool hasMessages;
  final Color accentColor;
  final VoidCallback onCopy;
  final VoidCallback onSave;
  final VoidCallback? onRemember;

  const HomeToolbar({
    super.key,
    required this.isVisible,
    required this.hasMessages,
    required this.accentColor,
    required this.onCopy,
    required this.onSave,
    this.onRemember,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return AnimatedSize(
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeOutCubic,
      child: isVisible && hasMessages
          ? Container(
              height: 56,
              margin: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
              decoration: BoxDecoration(
                // Stronger background for visibility without glassmorphic card
                color: isDark
                    ? Colors.white.withValues(alpha: 0.08)
                    : Colors.white.withValues(alpha: 0.85),
                borderRadius: BorderRadius.circular(GlassTheme.radiusLarge),
                border: Border.all(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.15)
                      : Colors.white.withValues(alpha: 0.5),
                  width: 1,
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: isDark ? 0.5 : 0.12),
                    blurRadius: 24,
                    offset: const Offset(0, 8),
                    spreadRadius: -4,
                  ),
                  BoxShadow(
                    color: accentColor.withValues(alpha: 0.15),
                    blurRadius: 32,
                    spreadRadius: -8,
                  ),
                ],
              ),
              child: Center(
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _ToolbarAction(
                      icon: Icons.content_copy_rounded,
                      onTap: onCopy,
                      accentColor: accentColor,
                      isEnabled: true,
                    ),
                    const SizedBox(width: 12),
                    _ToolbarAction(
                      icon: Icons.save_outlined,
                      onTap: onSave,
                      accentColor: accentColor,
                      isEnabled: true,
                    ),
                    const SizedBox(width: 12),
                    _ToolbarAction(
                      icon: Icons.auto_awesome_rounded,
                      onTap: onRemember ?? () {},
                      accentColor: accentColor,
                      isEnabled: onRemember != null,
                    ),
                  ],
                ),
              ),
            )
          : const SizedBox.shrink(),
    );
  }
}

class _ToolbarAction extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  final Color accentColor;
  final bool isEnabled;

  const _ToolbarAction({
    required this.icon,
    required this.onTap,
    required this.accentColor,
    this.isEnabled = true,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: isEnabled
            ? () {
                HapticFeedback.lightImpact();
                onTap();
              }
            : null,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          width: 44,
          height: 44,
          alignment: Alignment.center,
          child: Icon(
            icon,
            size: 22,
            color: isEnabled
                ? accentColor
                : theme.colorScheme.onSurface.withValues(alpha: 0.3),
          ),
        ),
      ),
    );
  }
}
