import 'package:aico_frontend/core/providers.dart';
import 'package:aico_frontend/domain/entities/conversation_audio_settings.dart';
import 'package:flutter/foundation.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'conversation_audio_settings_provider.g.dart';

/// Provider for conversation audio settings (input/reply channels, silent mode)
@riverpod
class ConversationAudioSettingsNotifier extends _$ConversationAudioSettingsNotifier {
  static const String _keyInputChannel = 'conversation_input_channel';
  static const String _keyReplyChannel = 'conversation_reply_channel';
  static const String _keySilentMode = 'conversation_silent_mode';

  @override
  ConversationAudioSettings build() {
    // Load persisted settings from SharedPreferences
    final prefs = ref.watch(sharedPreferencesProvider);
    
    final savedInputChannel = prefs.getString(_keyInputChannel);
    final savedReplyChannel = prefs.getString(_keyReplyChannel);
    final savedSilentMode = prefs.getBool(_keySilentMode) ?? false;
    
    final inputChannel = savedInputChannel != null
        ? InputChannel.values.firstWhere(
            (e) => e.name == savedInputChannel,
            orElse: () => InputChannel.text,
          )
        : InputChannel.text;
    
    final replyChannel = savedReplyChannel != null
        ? ReplyChannel.values.firstWhere(
            (e) => e.name == savedReplyChannel,
            orElse: () => ReplyChannel.textOnly,
          )
        : ReplyChannel.textOnly;
    
    debugPrint('[ConversationAudioSettings] Loaded: input=$inputChannel, reply=$replyChannel, silent=$savedSilentMode');
    
    return ConversationAudioSettings(
      inputChannel: inputChannel,
      replyChannel: replyChannel,
      isSilent: savedSilentMode,
    );
  }

  /// Set input channel (text vs voice)
  void setInputChannel(InputChannel channel) {
    if (state.inputChannel != channel) {
      state = state.copyWith(inputChannel: channel);
      _persist();
      debugPrint('[ConversationAudioSettings] Input channel: $channel');
    }
  }

  /// Set reply channel (text-only vs text+voice)
  void setReplyChannel(ReplyChannel channel) {
    if (state.replyChannel != channel) {
      state = state.copyWith(replyChannel: channel);
      _persist();
      debugPrint('[ConversationAudioSettings] Reply channel: $channel');
    }
  }

  /// Toggle reply channel between text-only and text+voice
  void toggleReplyChannel() {
    final newChannel = state.replyChannel == ReplyChannel.textOnly
        ? ReplyChannel.textAndVoice
        : ReplyChannel.textOnly;
    
    debugPrint('[ConversationAudioSettings] 🔊 Toggling reply channel: ${state.replyChannel} → $newChannel');
    
    // When enabling voice replies, also disable silent mode
    if (newChannel == ReplyChannel.textAndVoice && state.isSilent) {
      state = state.copyWith(
        replyChannel: newChannel,
        isSilent: false,
      );
      _persist();
      debugPrint('[ConversationAudioSettings] ✅ Reply channel: $newChannel, Silent mode disabled, shouldPlayTTS: ${state.shouldPlayTTS}');
    } else {
      setReplyChannel(newChannel);
      debugPrint('[ConversationAudioSettings] ✅ Reply channel: $newChannel, shouldPlayTTS: ${state.shouldPlayTTS}');
    }
  }

  /// Enable/disable silent mode (privacy mode)
  void setSilentMode(bool silent) {
    if (state.isSilent != silent) {
      state = state.copyWith(isSilent: silent);
      _persist();
      debugPrint('[ConversationAudioSettings] Silent mode: $silent');
    }
  }

  /// Toggle silent mode
  void toggleSilentMode() {
    setSilentMode(!state.isSilent);
  }

  /// Persist current settings to SharedPreferences
  void _persist() {
    final prefs = ref.read(sharedPreferencesProvider);
    prefs.setString(_keyInputChannel, state.inputChannel.name);
    prefs.setString(_keyReplyChannel, state.replyChannel.name);
    prefs.setBool(_keySilentMode, state.isSilent);
  }
}
