import 'package:equatable/equatable.dart';

/// Audio input channel for conversation
enum InputChannel {
  /// Text-based input (typing)
  text,
  
  /// Voice-based input (STT)
  voice,
}

/// Audio reply channel for AI responses
enum ReplyChannel {
  /// Text-only replies (no TTS)
  textOnly,
  
  /// Text + voice replies (TTS enabled)
  textAndVoice,
}

/// Immutable audio settings state for conversation
class ConversationAudioSettings extends Equatable {
  /// How the user provides input
  final InputChannel inputChannel;
  
  /// How the AI responds
  final ReplyChannel replyChannel;
  
  /// Privacy mode - forces text-only replies regardless of replyChannel
  final bool isSilent;

  const ConversationAudioSettings({
    this.inputChannel = InputChannel.text,
    this.replyChannel = ReplyChannel.textOnly,
    this.isSilent = false,
  });

  /// Whether TTS should play for AI responses
  bool get shouldPlayTTS => replyChannel == ReplyChannel.textAndVoice && !isSilent;

  /// Whether voice input is active
  bool get isVoiceInputActive => inputChannel == InputChannel.voice;

  ConversationAudioSettings copyWith({
    InputChannel? inputChannel,
    ReplyChannel? replyChannel,
    bool? isSilent,
  }) {
    return ConversationAudioSettings(
      inputChannel: inputChannel ?? this.inputChannel,
      replyChannel: replyChannel ?? this.replyChannel,
      isSilent: isSilent ?? this.isSilent,
    );
  }

  @override
  List<Object?> get props => [inputChannel, replyChannel, isSilent];
}
