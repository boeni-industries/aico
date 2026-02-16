import 'package:aico_frontend/data/models/proactive_model.dart';
import 'package:aico_frontend/presentation/providers/proactive_state_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Dialog for displaying proactive conversation initiation
class ProactiveNotificationDialog extends ConsumerStatefulWidget {
  final InitiationModel initiation;

  const ProactiveNotificationDialog({
    super.key,
    required this.initiation,
  });

  @override
  ConsumerState<ProactiveNotificationDialog> createState() =>
      _ProactiveNotificationDialogState();
}

class _ProactiveNotificationDialogState
    extends ConsumerState<ProactiveNotificationDialog> {
  final _responseController = TextEditingController();
  bool _isSubmitting = false;

  @override
  void dispose() {
    _responseController.dispose();
    super.dispose();
  }

  Future<void> _handleAnswer() async {
    if (_responseController.text.trim().isEmpty) return;

    setState(() => _isSubmitting = true);

    try {
      await ref.read(proactiveStateProvider.notifier).answerInitiation(
            initiationId: widget.initiation.initiationId,
            responseText: _responseController.text.trim(),
            engagementScore: 0.8, // Could be calculated based on response length/quality
          );

      if (mounted) {
        Navigator.of(context).pop();
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  Future<void> _handleDismiss() async {
    setState(() => _isSubmitting = true);

    try {
      await ref
          .read(proactiveStateProvider.notifier)
          .dismissInitiation(widget.initiation.initiationId);

      if (mounted) {
        Navigator.of(context).pop();
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  Future<void> _handleDefer() async {
    setState(() => _isSubmitting = true);

    try {
      await ref
          .read(proactiveStateProvider.notifier)
          .deferInitiation(widget.initiation.initiationId);

      if (mounted) {
        Navigator.of(context).pop();
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.chat_bubble_outline, size: 20),
          SizedBox(width: 8),
          Text('AICO wants to ask you'),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            widget.initiation.question,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _responseController,
            decoration: const InputDecoration(
              hintText: 'Your response...',
              border: OutlineInputBorder(),
            ),
            maxLines: 3,
            enabled: !_isSubmitting,
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: _isSubmitting ? null : _handleDismiss,
          child: const Text('Dismiss'),
        ),
        TextButton(
          onPressed: _isSubmitting ? null : _handleDefer,
          child: const Text('Later'),
        ),
        FilledButton(
          onPressed: _isSubmitting ? null : _handleAnswer,
          child: _isSubmitting
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Answer'),
        ),
      ],
    );
  }
}
