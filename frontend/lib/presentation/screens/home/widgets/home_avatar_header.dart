import 'package:aico_frontend/presentation/providers/avatar_state_provider.dart';
import 'package:aico_frontend/presentation/providers/conversation_provider.dart';
import 'package:aico_frontend/presentation/theme/glassmorphism.dart';
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
  Color _getAvatarMoodColor(AvatarMode mode, bool isDark) {
    switch (mode) {
      case AvatarMode.thinking:
        return widget.accentColor;
      case AvatarMode.speaking:
        return widget.accentColor.withValues(alpha: 0.8);
      case AvatarMode.idle:
      default:
        return widget.accentColor.withValues(alpha: 0.5);
    }
  }

  @override
  Widget build(BuildContext context) {
    final conversationState = ref.watch(conversationProvider);
    final avatarState = ref.watch(avatarRingStateProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;
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

    final avatarMoodColor = _getAvatarMoodColor(avatarState.mode, isDark);

    return AnimatedBuilder(
      animation: widget.glowController,
      builder: (context, child) {
        return Container(
          padding: const EdgeInsets.all(16),
          child: Container(
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              boxShadow: GlassTheme.pulsingGlow(
                color: avatarMoodColor,
                animationValue: widget.glowAnimation.value,
                baseIntensity: 0.2,
                pulseIntensity: 0.5,
              ),
            ),
            child: const CompanionAvatar(),
          ),
        );
      },
    );
  }
}
