import 'package:aico_frontend/presentation/providers/proactive_state_provider.dart';
import 'package:aico_frontend/presentation/widgets/proactive/proactive_notification_dialog.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Badge showing count of pending proactive initiations
class ProactiveNotificationBadge extends ConsumerWidget {
  const ProactiveNotificationBadge({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(proactiveStateProvider);
    final pendingCount = state.pendingInitiations.length;

    if (pendingCount == 0) {
      return const SizedBox.shrink();
    }

    return IconButton(
      icon: Badge(
        label: Text(pendingCount.toString()),
        child: const Icon(Icons.notifications_outlined),
      ),
      onPressed: () {
        // Show first pending initiation
        if (state.pendingInitiations.isNotEmpty) {
          showDialog(
            context: context,
            builder: (context) => ProactiveNotificationDialog(
              initiation: state.pendingInitiations.first,
            ),
          );
        }
      },
    );
  }
}
