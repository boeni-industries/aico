import 'package:flutter/material.dart';

class SystemStatusBar extends StatelessWidget {
  final bool isConnected;
  final String? statusMessage;
  final bool isCollapsed;
  final VoidCallback? onToggle;

  const SystemStatusBar({
    super.key,
    required this.isConnected,
    this.statusMessage,
    this.isCollapsed = false,
    this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      height: isCollapsed ? 40 : 60,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: _getStatusColor(theme).withValues(alpha: 0.1),
        border: Border(
          bottom: BorderSide(
            color: _getStatusColor(theme).withValues(alpha: 0.3),
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          // Status indicator
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: _getStatusColor(theme),
            ),
          ),
          const SizedBox(width: 12),
          // Status text
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  _getStatusText(),
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                    color: _getStatusColor(theme),
                  ),
                ),
                if (!isCollapsed && statusMessage != null)
                  Text(
                    statusMessage!,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
              ],
            ),
          ),
          // Toggle button
          if (onToggle != null)
            IconButton(
              onPressed: onToggle,
              icon: Icon(
                isCollapsed ? Icons.expand_more : Icons.expand_less,
                size: 20,
              ),
              style: IconButton.styleFrom(
                foregroundColor: theme.colorScheme.onSurfaceVariant,
                minimumSize: const Size(32, 32),
              ),
            ),
        ],
      ),
    );
  }

  Color _getStatusColor(ThemeData theme) {
    if (isConnected) {
      return Colors.green;
    } else {
      return Colors.orange;
    }
  }

  String _getStatusText() {
    if (isConnected) {
      return 'Connected';
    } else {
      return 'Connecting...';
    }
  }
}
