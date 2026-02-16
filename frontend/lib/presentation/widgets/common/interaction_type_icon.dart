import 'package:flutter/material.dart';

/// Reusable icon widget for interaction types
/// 
/// Provides consistent iconography and colors for different interaction types
class InteractionTypeIcon extends StatelessWidget {
  final String interactionType;
  final double size;
  final double? alpha;

  const InteractionTypeIcon({
    super.key,
    required this.interactionType,
    this.size = 20,
    this.alpha,
  });

  @override
  Widget build(BuildContext context) {
    final iconData = _getIconData();
    
    return Icon(
      iconData.icon,
      size: size,
      color: alpha != null 
          ? iconData.color.withValues(alpha: alpha!)
          : iconData.color.withValues(alpha: 0.8),
    );
  }

  _IconData _getIconData() {
    switch (interactionType) {
      case 'question':
        return _IconData(Icons.help_outline, Colors.blue);
      case 'choice':
        return _IconData(Icons.radio_button_checked, Colors.purple);
      case 'approval':
        return _IconData(Icons.check_circle_outline, Colors.orange);
      case 'dialogue':
        return _IconData(Icons.chat_bubble_outline, Colors.green);
      case 'ack':
        return _IconData(Icons.info_outline, Colors.grey);
      default:
        return _IconData(Icons.notifications_outlined, Colors.grey);
    }
  }

  /// Get icon data without creating widget (for use in other components)
  static IconData getIcon(String interactionType) {
    switch (interactionType) {
      case 'question':
        return Icons.help_outline;
      case 'choice':
        return Icons.radio_button_checked;
      case 'approval':
        return Icons.check_circle_outline;
      case 'dialogue':
        return Icons.chat_bubble_outline;
      case 'ack':
        return Icons.info_outline;
      default:
        return Icons.notifications_outlined;
    }
  }

  /// Get color for interaction type
  static Color getColor(String interactionType) {
    switch (interactionType) {
      case 'question':
        return Colors.blue;
      case 'choice':
        return Colors.purple;
      case 'approval':
        return Colors.orange;
      case 'dialogue':
        return Colors.green;
      case 'ack':
        return Colors.grey;
      default:
        return Colors.grey;
    }
  }
}

class _IconData {
  final IconData icon;
  final Color color;

  _IconData(this.icon, this.color);
}
