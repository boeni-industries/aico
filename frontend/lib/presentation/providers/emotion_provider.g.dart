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
///
/// Supports smart filtering:
/// - [limit]: Max records (default: 50)
/// - [hours]: Last N hours
/// - [days]: Last N days
/// - [since]: ISO timestamp
/// - [feeling]: Filter by emotion

@ProviderFor(emotionHistory)
const emotionHistoryProvider = EmotionHistoryFamily._();

/// Emotion history provider - fetches and caches emotion history
///
/// Supports smart filtering:
/// - [limit]: Max records (default: 50)
/// - [hours]: Last N hours
/// - [days]: Last N days
/// - [since]: ISO timestamp
/// - [feeling]: Filter by emotion

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
  ///
  /// Supports smart filtering:
  /// - [limit]: Max records (default: 50)
  /// - [hours]: Last N hours
  /// - [days]: Last N days
  /// - [since]: ISO timestamp
  /// - [feeling]: Filter by emotion
  const EmotionHistoryProvider._({
    required EmotionHistoryFamily super.from,
    required ({
      int limit,
      int? hours,
      int? days,
      String? since,
      String? feeling,
    })
    super.argument,
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
        '$argument';
  }

  @$internal
  @override
  $FutureProviderElement<List<EmotionHistoryItem>> $createElement(
    $ProviderPointer pointer,
  ) => $FutureProviderElement(pointer);

  @override
  FutureOr<List<EmotionHistoryItem>> create(Ref ref) {
    final argument =
        this.argument
            as ({
              int limit,
              int? hours,
              int? days,
              String? since,
              String? feeling,
            });
    return emotionHistory(
      ref,
      limit: argument.limit,
      hours: argument.hours,
      days: argument.days,
      since: argument.since,
      feeling: argument.feeling,
    );
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

String _$emotionHistoryHash() => r'0aa953e8e08de86143a4f5304e151d28af9aa7d7';

/// Emotion history provider - fetches and caches emotion history
///
/// Supports smart filtering:
/// - [limit]: Max records (default: 50)
/// - [hours]: Last N hours
/// - [days]: Last N days
/// - [since]: ISO timestamp
/// - [feeling]: Filter by emotion

final class EmotionHistoryFamily extends $Family
    with
        $FunctionalFamilyOverride<
          FutureOr<List<EmotionHistoryItem>>,
          ({int limit, int? hours, int? days, String? since, String? feeling})
        > {
  const EmotionHistoryFamily._()
    : super(
        retry: null,
        name: r'emotionHistoryProvider',
        dependencies: null,
        $allTransitiveDependencies: null,
        isAutoDispose: true,
      );

  /// Emotion history provider - fetches and caches emotion history
  ///
  /// Supports smart filtering:
  /// - [limit]: Max records (default: 50)
  /// - [hours]: Last N hours
  /// - [days]: Last N days
  /// - [since]: ISO timestamp
  /// - [feeling]: Filter by emotion

  EmotionHistoryProvider call({
    int limit = 50,
    int? hours,
    int? days,
    String? since,
    String? feeling,
  }) => EmotionHistoryProvider._(
    argument: (
      limit: limit,
      hours: hours,
      days: days,
      since: since,
      feeling: feeling,
    ),
    from: this,
  );

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

String _$emotionStateHash() => r'ba693230a354a93f603925cf0a8af62faab6f96c';

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
