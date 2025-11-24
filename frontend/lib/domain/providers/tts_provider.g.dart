// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'tts_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// TTS repository provider

@ProviderFor(ttsRepository)
const ttsRepositoryProvider = TtsRepositoryProvider._();

/// TTS repository provider

final class TtsRepositoryProvider
    extends $FunctionalProvider<TtsRepository, TtsRepository, TtsRepository>
    with $Provider<TtsRepository> {
  /// TTS repository provider
  const TtsRepositoryProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'ttsRepositoryProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$ttsRepositoryHash();

  @$internal
  @override
  $ProviderElement<TtsRepository> $createElement($ProviderPointer pointer) =>
      $ProviderElement(pointer);

  @override
  TtsRepository create(Ref ref) {
    return ttsRepository(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(TtsRepository value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<TtsRepository>(value),
    );
  }
}

String _$ttsRepositoryHash() => r'c9e2c7ba21c5959bbd6137e316c2fec0b10b56b0';

/// TTS state notifier using modern Riverpod pattern

@ProviderFor(Tts)
const ttsProvider = TtsProvider._();

/// TTS state notifier using modern Riverpod pattern
final class TtsProvider extends $NotifierProvider<Tts, TtsState> {
  /// TTS state notifier using modern Riverpod pattern
  const TtsProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'ttsProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$ttsHash();

  @$internal
  @override
  Tts create() => Tts();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(TtsState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<TtsState>(value),
    );
  }
}

String _$ttsHash() => r'20e7027fe88429fc3b17be987751f0b6dec6adb1';

/// TTS state notifier using modern Riverpod pattern

abstract class _$Tts extends $Notifier<TtsState> {
  TtsState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<TtsState, TtsState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<TtsState, TtsState>,
              TtsState,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
