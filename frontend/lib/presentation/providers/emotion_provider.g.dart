// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'emotion_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Repository provider

@ProviderFor(emotionRepository)
const emotionRepositoryProvider = EmotionRepositoryProvider._();

/// Repository provider

final class EmotionRepositoryProvider
    extends
        $FunctionalProvider<
          EmotionRepository,
          EmotionRepository,
          EmotionRepository
        >
    with $Provider<EmotionRepository> {
  /// Repository provider
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

String _$emotionRepositoryHash() => r'9179701d2d27a4433b53ee94eb5e2986ce1a167d';

/// Emotion history provider - fetches and caches emotion history

@ProviderFor(emotionHistory)
const emotionHistoryProvider = EmotionHistoryFamily._();

/// Emotion history provider - fetches and caches emotion history

final class EmotionHistoryProvider
    extends
        $FunctionalProvider<
          AsyncValue<List<EmotionHistoryItem>>,
          List<EmotionHistoryItem>,
          FutureOr<List<EmotionHistoryItem>>
        >
    with
        $FutureModifier<List<EmotionHistoryItem>>,
        $FutureProvider<List<EmotionHistoryItem>> {
  /// Emotion history provider - fetches and caches emotion history
  const EmotionHistoryProvider._({
    required EmotionHistoryFamily super.from,
    required int super.argument,
  }) : super(
         retry: null,
         name: r'emotionHistoryProvider',
         isAutoDispose: true,
         dependencies: null,
         $allTransitiveDependencies: null,
       );

  @override
  String debugGetCreateSourceHash() => _$emotionHistoryHash();

  @override
  String toString() {
    return r'emotionHistoryProvider'
        ''
        '($argument)';
  }

  @$internal
  @override
  $FutureProviderElement<List<EmotionHistoryItem>> $createElement(
    $ProviderPointer pointer,
  ) => $FutureProviderElement(pointer);

  @override
  FutureOr<List<EmotionHistoryItem>> create(Ref ref) {
    final argument = this.argument as int;
    return emotionHistory(ref, limit: argument);
  }

  @override
  bool operator ==(Object other) {
    return other is EmotionHistoryProvider && other.argument == argument;
  }

  @override
  int get hashCode {
    return argument.hashCode;
  }
}

String _$emotionHistoryHash() => r'67cebddf3aebb153f15515a542870ac5eb685280';

/// Emotion history provider - fetches and caches emotion history

final class EmotionHistoryFamily extends $Family
    with $FunctionalFamilyOverride<FutureOr<List<EmotionHistoryItem>>, int> {
  const EmotionHistoryFamily._()
    : super(
        retry: null,
        name: r'emotionHistoryProvider',
        dependencies: null,
        $allTransitiveDependencies: null,
        isAutoDispose: true,
      );

  /// Emotion history provider - fetches and caches emotion history

  EmotionHistoryProvider call({int limit = 50}) =>
      EmotionHistoryProvider._(argument: limit, from: this);

  @override
  String toString() => r'emotionHistoryProvider';
}

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

String _$emotionStateHash() => r'6ebb76828bd17ad23ecaf3b82bb08bc3b0ebe5d5';

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
