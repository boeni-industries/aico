import 'package:flutter/material.dart';

/// Settings screen placeholder.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.settings,
            size: 64,
            color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
          ),
          const SizedBox(height: 24),
          Text(
            'Not Implemented Yet',
            style: theme.textTheme.headlineMedium?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
