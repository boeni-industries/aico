import 'package:aico_frontend/presentation/providers/settings_provider.dart';
import 'package:aico_frontend/presentation/providers/conversation_provider.dart';
import 'package:aico_frontend/core/widgets/atoms/aico_button.dart';
import 'package:aico_frontend/presentation/widgets/common/glassmorphic_card.dart';
import 'package:aico_frontend/presentation/widgets/common/glassmorphic_switch.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Settings screen with thinking display toggle
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  Future<bool?> _confirmClearCache(BuildContext context) {
    return showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Clear local chat cache?'),
          content: const Text(
            'This will delete all locally stored conversation history on this device. This cannot be undone.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Clear'),
            ),
          ],
        );
      },
    );
  }

  Widget _sectionTitle(BuildContext context, String title) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Text(
        title,
        style: theme.textTheme.titleMedium?.copyWith(
          fontWeight: FontWeight.w600,
          letterSpacing: 0.2,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final settings = ref.watch(settingsProvider);
    final isDark = theme.brightness == Brightness.dark;
    
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text(
          'Settings',
          style: theme.textTheme.headlineMedium?.copyWith(
            fontWeight: FontWeight.w700,
            letterSpacing: 0.2,
          ),
        ),
        const SizedBox(height: 20),

        _sectionTitle(context, 'AI Behavior'),
        GlassmorphicCard(
          padding: const EdgeInsets.all(18),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      'Show Inner Monologue',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Display AI thinking process in the right drawer',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.onSurface.withValues(alpha: isDark ? 0.72 : 0.75),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              GlassmorphicSwitch(
                value: settings.showThinking,
                onChanged: (value) {
                  ref.read(settingsProvider.notifier).updateShowThinking(value);
                },
              ),
            ],
          ),
        ),

        const SizedBox(height: 28),

        _sectionTitle(context, 'Data'),
        GlassmorphicCard(
          padding: const EdgeInsets.all(18),
          child: LayoutBuilder(
            builder: (context, constraints) {
              final isCompact = constraints.maxWidth < 520;

              final content = Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'Clear local chat cache',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Deletes conversation history stored on this device',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurface.withValues(alpha: isDark ? 0.72 : 0.75),
                    ),
                  ),
                ],
              );

              final action = AicoButton.destructive(
                width: isCompact ? double.infinity : 180,
                height: 44,
                onPressed: () async {
                  final confirmed = await _confirmClearCache(context);
                  if (confirmed != true) return;
                  await ref.read(conversationProvider.notifier).clearLocalHistory();
                },
                child: const Text('Clear cache'),
              );

              if (isCompact) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    content,
                    const SizedBox(height: 14),
                    action,
                  ],
                );
              }

              return Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Expanded(child: content),
                  const SizedBox(width: 18),
                  action,
                ],
              );
            },
          ),
        ),

        const SizedBox(height: 28),

        Text(
          'More settings coming soon...',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
          ),
        ),
      ],
    );
  }
}
