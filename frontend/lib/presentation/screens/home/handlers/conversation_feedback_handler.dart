import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../providers/behavioral_feedback_provider.dart';
import '../../../widgets/chat/feedback_dialog.dart';
import '../../../widgets/common/glassmorphic_toast.dart';

/// Handler for behavioral feedback submission
/// 
/// Manages:
/// - Immediate feedback submission (thumbs up/down)
/// - Detailed feedback dialog display
/// - Success/error toast notifications
class ConversationFeedbackHandler {
  final BuildContext context;
  final WidgetRef ref;
  final Color accentColor;

  ConversationFeedbackHandler({
    required this.context,
    required this.ref,
    required this.accentColor,
  });

  /// Handle behavioral feedback submission
  Future<void> handleFeedback(String messageId, bool isPositive) async {
    // Submit immediate feedback (thumbs only)
    final success = await ref.read(behavioralFeedbackProvider.notifier).submitFeedback(
      messageId: messageId,
      isPositive: isPositive,
    );
    
    if (!success) {
      // Show elegant glassmorphic toast for errors
      if (!context.mounted) return;
      GlassmorphicToast.show(
        context,
        message: 'Failed to submit feedback',
        icon: Icons.error_outline_rounded,
        accentColor: Colors.red.shade400,
        duration: const Duration(seconds: 2),
      );
      return;
    }
    
    // Show detailed feedback dialog
    if (!context.mounted) return;
    
    showDialog(
      context: context,
      barrierColor: Colors.transparent, // Dialog has its own backdrop
      builder: (context) => FeedbackDialog(
        isPositive: isPositive,
        messageId: messageId,
        accentColor: accentColor,
        onSubmit: (reason, freeText) async {
          // Submit detailed feedback
          await ref.read(behavioralFeedbackProvider.notifier).submitFeedback(
            messageId: messageId,
            isPositive: isPositive,
            reason: reason,
            freeText: freeText,
          );
          
          // Show elegant glassmorphic toast for success
          if (!context.mounted) return;
          GlassmorphicToast.show(
            context,
            message: 'Thank you for your feedback!',
            icon: Icons.check_circle_outline_rounded,
            accentColor: accentColor,
            duration: const Duration(seconds: 2),
          );
        },
      ),
    );
  }
}
