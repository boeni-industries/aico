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
    // Match the ring colors from companion_avatar.dart
    const emerald = Color(0xFF10B981);
    const purple = Color(0xFFB8A1EA);
    const sapphire = Color(0xFF3B82F6);
    const coral = Color(0xFFED7867);
    const amber = Color(0xFFF59E0B);
    const violet = Color(0xFF8B5CF6);
    
    switch (mode) {
      case AvatarMode.thinking:
      case AvatarMode.speaking:
        return purple;
      case AvatarMode.processing:
        return violet;
      case AvatarMode.listening:
        return sapphire;
      case AvatarMode.success:
        return emerald;
      case AvatarMode.error:
        return coral;
      case AvatarMode.attention:
        return amber;
      case AvatarMode.connecting:
        return sapphire;
      case AvatarMode.idle:
        return emerald; // Green for idle, matching the ring
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
