// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'conversation_audio_settings_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Provider for conversation audio settings (input/reply channels, silent mode)

@ProviderFor(ConversationAudioSettingsNotifier)
const conversationAudioSettingsProvider =
    ConversationAudioSettingsNotifierProvider._();

/// Provider for conversation audio settings (input/reply channels, silent mode)
final class ConversationAudioSettingsNotifierProvider
    extends
        $NotifierProvider<
          ConversationAudioSettingsNotifier,
          ConversationAudioSettings
        > {
  /// Provider for conversation audio settings (input/reply channels, silent mode)
  const ConversationAudioSettingsNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'conversationAudioSettingsProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() =>
      _$conversationAudioSettingsNotifierHash();

  @$internal
  @override
  ConversationAudioSettingsNotifier create() =>
      ConversationAudioSettingsNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ConversationAudioSettings value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ConversationAudioSettings>(value),
    );
  }
}

String _$conversationAudioSettingsNotifierHash() =>
    r'0e90c8d8e13bb69d6d60d30e8d5069e81181cab1';

/// Provider for conversation audio settings (input/reply channels, silent mode)

abstract class _$ConversationAudioSettingsNotifier
    extends $Notifier<ConversationAudioSettings> {
  ConversationAudioSettings build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref =
        this.ref as $Ref<ConversationAudioSettings, ConversationAudioSettings>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<ConversationAudioSettings, ConversationAudioSettings>,
              ConversationAudioSettings,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
