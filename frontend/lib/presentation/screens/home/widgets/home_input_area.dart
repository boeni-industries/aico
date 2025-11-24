import 'dart:ui';

import 'package:aico_frontend/domain/entities/conversation_audio_settings.dart';
import 'package:aico_frontend/presentation/providers/conversation_audio_settings_provider.dart';
import 'package:aico_frontend/presentation/providers/conversation_provider.dart';
import 'package:aico_frontend/presentation/providers/layout_provider.dart';
import 'package:aico_frontend/presentation/theme/glassmorphism.dart';
import 'package:aico_frontend/presentation/widgets/common/animated_button.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Message input area with glassmorphic styling and audio controls
class HomeInputArea extends ConsumerWidget {
  final TextEditingController controller;
  final FocusNode focusNode;
  final Color accentColor;
  final VoidCallback onSend;
  final VoidCallback onVoice;
  final GlobalKey sendButtonKey;
  final GlobalKey voiceButtonKey;

  const HomeInputArea({
    super.key,
    required this.controller,
    required this.focusNode,
    required this.accentColor,
    required this.onSend,
    required this.onVoice,
    required this.sendButtonKey,
    required this.voiceButtonKey,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final conversationState = ref.watch(conversationProvider);
    final layoutState = ref.watch(layoutProvider);
    final audioSettings = ref.watch(conversationAudioSettingsProvider);
    final isActive = conversationState.isSendingMessage || conversationState.isStreaming;
    final isVoiceMode = layoutState.modality == ConversationModality.voice;
    final isSpeakerEnabled = audioSettings.replyChannel == ReplyChannel.textAndVoice && !audioSettings.isSilent;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 0, vertical: 12),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
        child: BackdropFilter(
          filter: ImageFilter.blur(
            sigmaX: GlassTheme.blurHeavy,
            sigmaY: GlassTheme.blurHeavy,
          ),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            decoration: BoxDecoration(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.06)
                  : Colors.white.withValues(alpha: 0.7),
              borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
              border: Border.all(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.12)
                    : Colors.white.withValues(alpha: 0.5),
                width: 1.5,
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.08),
                  blurRadius: 32,
                  offset: const Offset(0, 12),
                  spreadRadius: -8,
                ),
              ],
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: controller,
                    focusNode: focusNode,
                    autofocus: true,
                    maxLines: null,
                    textInputAction: TextInputAction.send,
                    decoration: InputDecoration(
                      hintText: 'Share what\'s on your mind...',
                      border: InputBorder.none,
                      hintStyle: TextStyle(
                        color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                        fontSize: 15,
                        letterSpacing: 0.3,
                      ),
                    ),
                    style: const TextStyle(
                      fontSize: 15,
                      height: 1.5,
                      letterSpacing: 0.2,
                    ),
                    onSubmitted: (_) => onSend(),
                    onEditingComplete: () {
                      final text = controller.text.trim();
                      if (text.isNotEmpty) {
                        onSend();
                      }
                    },
                  ),
                ),
                const SizedBox(width: 12),
                // Speaker toggle (reply channel control)
                AnimatedButton(
                  onPressed: () {
                    ref.read(conversationAudioSettingsProvider.notifier).toggleReplyChannel();
                  },
                  icon: isSpeakerEnabled ? Icons.volume_up_rounded : Icons.volume_off_rounded,
                  size: 48,
                  foregroundColor: isSpeakerEnabled 
                      ? accentColor 
                      : theme.colorScheme.onSurface.withValues(alpha: 0.4),
                  isEnabled: !isActive,
                  tooltip: isSpeakerEnabled ? 'Voice replies enabled' : 'Voice replies muted',
                ),
                const SizedBox(width: 8),
                // Mic/Keyboard toggle (input channel + layout)
                AnimatedButton(
                  key: voiceButtonKey,
                  onPressed: onVoice,
                  icon: isVoiceMode ? Icons.keyboard_rounded : Icons.mic_rounded,
                  size: 48,
                  foregroundColor: isVoiceMode ? accentColor : theme.colorScheme.onSurface.withValues(alpha: 0.6),
                  isEnabled: !isActive,
                  tooltip: isVoiceMode ? 'Switch to text mode' : 'Switch to voice mode',
                ),
                const SizedBox(width: 8),
                // Send button
                AnimatedButton(
                  key: sendButtonKey,
                  onPressed: onSend,
                  icon: Icons.arrow_upward_rounded,
                  size: 48,
                  foregroundColor: accentColor,
                  isEnabled: !isActive,
                  tooltip: 'Send message',
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
