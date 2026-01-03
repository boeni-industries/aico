import 'package:aico_frontend/presentation/providers/agency_state_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Demo widget to test Agency Badge visibility
/// Place this in your main screen to trigger badge display
class AgencyBadgeDemo extends ConsumerWidget {
  const AgencyBadgeDemo({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            'Agency Badge Demo',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              ElevatedButton(
                onPressed: () {
                  ref.read(agencyBadgeStateProvider.notifier)
                    .showActiveIntention(
                      summary: "Helping with agency module",
                      intensity: 0.7,
                    );
                },
                child: const Text('Active Intention'),
              ),
              ElevatedButton(
                onPressed: () {
                  ref.read(agencyBadgeStateProvider.notifier)
                    .showLessonPending(count: 3);
                },
                child: const Text('Lesson Pending'),
              ),
              ElevatedButton(
                onPressed: () {
                  ref.read(agencyBadgeStateProvider.notifier)
                    .showGoalProgress(
                      progress: 0.65,
                      goalName: "Master agency system",
                    );
                },
                child: const Text('Goal Progress'),
              ),
              ElevatedButton(
                onPressed: () {
                  ref.read(agencyBadgeStateProvider.notifier)
                    .showGoalCompleted(
                      goalName: "Task complete!",
                    );
                },
                child: const Text('Goal Completed'),
              ),
              ElevatedButton(
                onPressed: () {
                  ref.read(agencyBadgeStateProvider.notifier)
                    .showMultipleItems(
                      count: 5,
                      summary: "Multiple items",
                    );
                },
                child: const Text('Multiple Items'),
              ),
              ElevatedButton(
                onPressed: () {
                  ref.read(agencyBadgeStateProvider.notifier).hide();
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.red.shade700,
                ),
                child: const Text('Hide Badge'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
