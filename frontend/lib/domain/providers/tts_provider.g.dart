// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'tts_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// TTS remote datasource provider

@ProviderFor(ttsRemoteDataSource)
const ttsRemoteDataSourceProvider = TtsRemoteDataSourceProvider._();

/// TTS remote datasource provider

final class TtsRemoteDataSourceProvider
    extends
        $FunctionalProvider<
          TtsRemoteDataSource,
          TtsRemoteDataSource,
          TtsRemoteDataSource
        >
    with $Provider<TtsRemoteDataSource> {
  /// TTS remote datasource provider
  const TtsRemoteDataSourceProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'ttsRemoteDataSourceProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$ttsRemoteDataSourceHash();

  @$internal
  @override
  $ProviderElement<TtsRemoteDataSource> $createElement(
    $ProviderPointer pointer,
  ) => $ProviderElement(pointer);

  @override
  TtsRemoteDataSource create(Ref ref) {
    return ttsRemoteDataSource(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(TtsRemoteDataSource value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<TtsRemoteDataSource>(value),
    );
  }
}

String _$ttsRemoteDataSourceHash() =>
    r'fd72e46c49fdc8b3bc491e320275e451b3dc0549';

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

String _$ttsRepositoryHash() => r'ab32648169878fceffa24f6279c99e225f22b98c';

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

String _$ttsHash() => r'65ec5d21415e8e9342992a45855459722d593f11';

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
