import 'package:flutter/material.dart';

/// Custom tab widget with glassmorphic hover effects
class GlassmorphicTab extends StatefulWidget {
  final String label;
  final bool isSelected;
  final VoidCallback onTap;
  
  const GlassmorphicTab({
    super.key,
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  @override
  State<GlassmorphicTab> createState() => _GlassmorphicTabState();
}

class _GlassmorphicTabState extends State<GlassmorphicTab> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final accentColor = theme.colorScheme.primary;

    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            // Show background when selected OR hovered
            color: widget.isSelected
                ? accentColor.withOpacity(0.15)
                : _isHovered
                    ? accentColor.withOpacity(0.08)
                    : Colors.transparent,
            border: widget.isSelected
                ? Border.all(
                    color: accentColor.withOpacity(0.3),
                    width: 1,
                  )
                : null,
          ),
          child: Center(
            child: Text(
              widget.label,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: widget.isSelected ? FontWeight.w600 : FontWeight.normal,
                color: widget.isSelected
                    ? accentColor
                    : theme.colorScheme.onSurface.withOpacity(0.6),
                letterSpacing: 0.3,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
