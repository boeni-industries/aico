import 'package:flutter/material.dart';

/// Reusable status badge widget
/// 
/// Displays a colored badge with label, commonly used for status indicators
class StatusBadge extends StatelessWidget {
  final String label;
  final Color color;
  final double fontSize;
  final FontWeight fontWeight;
  final EdgeInsetsGeometry? padding;

  const StatusBadge({
    super.key,
    required this.label,
    required this.color,
    this.fontSize = 9,
    this.fontWeight = FontWeight.w600,
    this.padding,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Container(
      padding: padding ?? const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: theme.textTheme.labelSmall?.copyWith(
          color: color,
          fontSize: fontSize,
          fontWeight: fontWeight,
        ),
      ),
    );
  }

  /// Factory for interaction status badges
  factory StatusBadge.interactionStatus(String status, {double? fontSize}) {
    Color color;
    String label;

    switch (status) {
      case 'pending':
        color = const Color(0xFFB8A1EA); // Purple accent
        label = 'Pending';
        break;
      case 'answered':
        color = const Color(0xFF8DD686); // Green
        label = 'Answered';
        break;
      case 'approved':
        color = const Color(0xFF8DD686); // Green
        label = 'Approved';
        break;
      case 'rejected':
        color = const Color(0xFFED7867); // Red
        label = 'Rejected';
        break;
      case 'dismissed':
        color = Colors.grey;
        label = 'Dismissed';
        break;
      case 'deferred':
        color = const Color(0xFFED7867); // Orange/Red
        label = 'Deferred';
        break;
      case 'expired':
        color = Colors.grey;
        label = 'Expired';
        break;
      case 'cancelled':
        color = Colors.grey;
        label = 'Cancelled';
        break;
      default:
        color = Colors.grey;
        label = status;
    }

    return StatusBadge(
      label: label,
      color: color,
      fontSize: fontSize ?? 9,
    );
  }
}
