import 'package:aico_frontend/presentation/providers/avatar_state_provider.dart';
import 'package:aico_frontend/presentation/providers/conversation_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Helper functions for HomeScreen
class HomeScreenHelpers {
  /// Get avatar mood color based on current mode
  static Color getAvatarMoodColor(AvatarMode mode, bool isDark) {
    const coral = Color(0xFFED7867);
    const emerald = Color(0xFF10B981);
    const amber = Color(0xFFF59E0B);
    const sapphire = Color(0xFF3B82F6);
    const purple = Color(0xFFB8A1EA);
    const violet = Color(0xFF8B5CF6);
    
    switch (mode) {
      case AvatarMode.thinking:
        return purple;
      case AvatarMode.processing:
        return violet;
      case AvatarMode.listening:
        return sapphire;
      case AvatarMode.speaking:
        return purple;
      case AvatarMode.success:
        return emerald;
      case AvatarMode.error:
        return coral;
      case AvatarMode.attention:
        return amber;
      case AvatarMode.connecting:
        return sapphire;
      case AvatarMode.idle:
        return emerald;
    }
  }

  /// Send a message through the conversation provider
  static Future<void> sendMessage({
    required WidgetRef ref,
    required String text,
    required TextEditingController controller,
    required FocusNode focusNode,
    required GlobalKey sendButtonKey,
  }) async {
    final trimmedText = text.trim();
    if (trimmedText.isEmpty) return;
    
    // Clear input immediately for better UX
    controller.clear();
    focusNode.requestFocus();
    
    // Show success animation immediately after send
    Future.delayed(const Duration(milliseconds: 100), () {
      final state = sendButtonKey.currentState;
      if (state != null && state.mounted) {
        (state as dynamic).showSuccess();
      }
    });
    
    // Send message via provider with streaming enabled
    await ref.read(conversationProvider.notifier).sendMessage(trimmedText, stream: true);
  }

  /// Scroll to bottom of conversation with smooth, gentle animation
  static void scrollToBottom(ScrollController controller, {bool instant = false}) {
    // Use a delay to ensure content is fully rendered (especially for fade animations)
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Future.delayed(Duration(milliseconds: instant ? 700 : 100), () {
        if (controller.hasClients && controller.position.maxScrollExtent > 0) {
          if (instant) {
            // Jump instantly to absolute bottom for initial load
            controller.jumpTo(controller.position.maxScrollExtent);
            // Double-check after a moment to ensure we're at the bottom
            Future.delayed(const Duration(milliseconds: 100), () {
              if (controller.hasClients) {
                controller.jumpTo(controller.position.maxScrollExtent);
              }
            });
          } else {
            // Smooth, gentle scroll for new messages
            controller.animateTo(
              controller.position.maxScrollExtent,
              duration: const Duration(milliseconds: 800),
              curve: Curves.easeInOutCubic,
            );
          }
        }
      });
    });
  }
}
