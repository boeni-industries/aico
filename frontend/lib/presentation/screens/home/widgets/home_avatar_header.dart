import 'package:aico_frontend/presentation/providers/avatar_state_provider.dart';
import 'package:aico_frontend/presentation/providers/conversation_provider.dart';
import 'package:aico_frontend/presentation/providers/layout_provider.dart';
import 'package:aico_frontend/presentation/widgets/avatar/companion_avatar.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Avatar header with ambient glow and thinking indicator
class HomeAvatarHeader extends ConsumerStatefulWidget {
  final Color accentColor;
  final AnimationController glowController;
  final Animation<double> glowAnimation;

  const HomeAvatarHeader({
    super.key,
    required this.accentColor,
    required this.glowController,
    required this.glowAnimation,
  });

  @override
  ConsumerState<HomeAvatarHeader> createState() => _HomeAvatarHeaderState();
}

class _HomeAvatarHeaderState extends ConsumerState<HomeAvatarHeader> {
  @override
  Widget build(BuildContext context) {
    final conversationState = ref.watch(conversationProvider);
    final avatarState = ref.watch(avatarRingStateProvider);
    final layoutState = ref.watch(layoutProvider);
    final isThinking = conversationState.isSendingMessage || conversationState.isStreaming;

    // Sync avatar mode with thinking state
    if (isThinking && avatarState.mode != AvatarMode.thinking) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(avatarRingStateProvider.notifier).startThinking(intensity: 0.8);
      });
    } else if (!isThinking && avatarState.mode == AvatarMode.thinking) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(avatarRingStateProvider.notifier).returnToIdle();
      });
    }

    return AnimatedBuilder(
      animation: widget.glowController,
      builder: (context, child) {
        // In text mode: center alignment
        // In voice mode: top-center to maximize viewport (from top to input area)
        final alignment = layoutState.modality == ConversationModality.text
            ? Alignment.center // Center for text mode
            : Alignment.topCenter; // Top-aligned in voice mode for maximum viewport
        
        return Align(
          alignment: alignment,
          child: const CompanionAvatar(), // Full-body with seamless aura
        );
      },
    );
  }
}
