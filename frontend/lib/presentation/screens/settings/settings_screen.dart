import 'package:aico_frontend/presentation/providers/settings_provider.dart';
import 'package:aico_frontend/presentation/widgets/common/glassmorphic_switch.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Settings screen with thinking display toggle
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final settings = ref.watch(settingsProvider);
    
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text(
          'Settings',
          style: theme.textTheme.headlineMedium?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 24),
        
        // AI Behavior Section
        Text(
          'AI Behavior',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        
        ListTile(
          title: const Text('Show Inner Monologue'),
          subtitle: const Text('Display AI thinking process in right drawer'),
          trailing: GlassmorphicSwitch(
            value: settings.showThinking,
            onChanged: (value) {
              ref.read(settingsProvider.notifier).updateShowThinking(value);
            },
          ),
        ),
        
        const Divider(height: 32),
        
        // Placeholder for future settings
        Text(
          'More settings coming soon...',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurface.withOpacity(0.5),
          ),
        ),
      ],
    );
  }
}
