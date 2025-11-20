// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'emotion_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Provider for emotion repository

@ProviderFor(emotionRepository)
const emotionRepositoryProvider = EmotionRepositoryProvider._();

/// Provider for emotion repository

final class EmotionRepositoryProvider
    extends
        $FunctionalProvider<
          EmotionRepository,
          EmotionRepository,
          EmotionRepository
        >
    with $Provider<EmotionRepository> {
  /// Provider for emotion repository
  const EmotionRepositoryProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'emotionRepositoryProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$emotionRepositoryHash();

  @$internal
  @override
  $ProviderElement<EmotionRepository> $createElement(
    $ProviderPointer pointer,
  ) => $ProviderElement(pointer);

  @override
  EmotionRepository create(Ref ref) {
    return emotionRepository(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(EmotionRepository value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<EmotionRepository>(value),
    );
  }
}

String _$emotionRepositoryHash() => r'8c3bc9f720449e91a1c89eb76e689db1a154e2a6';

/// Provider for current emotion state with polling

@ProviderFor(EmotionState)
const emotionStateProvider = EmotionStateProvider._();

/// Provider for current emotion state with polling
final class EmotionStateProvider
    extends $NotifierProvider<EmotionState, EmotionModel?> {
  /// Provider for current emotion state with polling
  const EmotionStateProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'emotionStateProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$emotionStateHash();

  @$internal
  @override
  EmotionState create() => EmotionState();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(EmotionModel? value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<EmotionModel?>(value),
    );
  }
}

String _$emotionStateHash() => r'd5515ddb88e6d157356078125c5a1e7d89d5bcc2';

/// Provider for current emotion state with polling

abstract class _$EmotionState extends $Notifier<EmotionModel?> {
  EmotionModel? build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<EmotionModel?, EmotionModel?>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<EmotionModel?, EmotionModel?>,
              EmotionModel?,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
