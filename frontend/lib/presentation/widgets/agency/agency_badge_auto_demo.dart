import 'dart:async';

import 'package:aico_frontend/presentation/providers/agency_state_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Auto-cycling demo mode for Agency Badge
/// Cycles through all badge states every 3 seconds
class AgencyBadgeAutoDemo extends ConsumerStatefulWidget {
  const AgencyBadgeAutoDemo({super.key});

  @override
  ConsumerState<AgencyBadgeAutoDemo> createState() => _AgencyBadgeAutoDemoState();
}

class _AgencyBadgeAutoDemoState extends ConsumerState<AgencyBadgeAutoDemo> {
  Timer? _cycleTimer;
  int _currentStateIndex = 0;
  
  final List<_DemoState> _demoStates = [
    _DemoState(
      name: 'Active Intention',
      trigger: (notifier) => notifier.showActiveIntention(
        summary: "Analyzing conversation patterns",
        intensity: 0.75,
      ),
    ),
    _DemoState(
      name: 'Lesson Pending',
      trigger: (notifier) => notifier.showLessonPending(count: 2),
    ),
    _DemoState(
      name: 'Goal Progress',
      trigger: (notifier) => notifier.showGoalProgress(
        progress: 0.65,
        goalName: "Improve response quality",
      ),
    ),
    _DemoState(
      name: 'Goal Completed',
      trigger: (notifier) => notifier.showGoalCompleted(
        goalName: "Daily interaction goal",
      ),
    ),
    _DemoState(
      name: 'Multiple Items',
      trigger: (notifier) => notifier.showMultipleItems(
        count: 5,
        summary: "Multiple pending items",
      ),
    ),
  ];

  @override
  void initState() {
    super.initState();
    // Delay provider modification until after widget tree is built
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _startCycling();
      }
    });
  }

  @override
  void dispose() {
    _cycleTimer?.cancel();
    super.dispose();
  }

  void _startCycling() {
    // Trigger first state immediately
    _triggerCurrentState();
    
    // Cycle every 3 seconds
    _cycleTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      if (mounted) {
        setState(() {
          _currentStateIndex = (_currentStateIndex + 1) % _demoStates.length;
        });
        _triggerCurrentState();
      }
    });
  }

  void _triggerCurrentState() {
    final notifier = ref.read(agencyBadgeStateProvider.notifier);
    _demoStates[_currentStateIndex].trigger(notifier);
  }

  @override
  Widget build(BuildContext context) {
    // Demo cycling only - no visual label
    return const SizedBox.shrink();
  }
}

class _DemoState {
  final String name;
  final void Function(AgencyBadgeStateNotifier) trigger;

  _DemoState({
    required this.name,
    required this.trigger,
  });
}
