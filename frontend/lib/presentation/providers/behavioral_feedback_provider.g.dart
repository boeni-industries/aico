// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'behavioral_feedback_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Provider for behavioral remote datasource

@ProviderFor(behavioralRemoteDataSource)
const behavioralRemoteDataSourceProvider =
    BehavioralRemoteDataSourceProvider._();

/// Provider for behavioral remote datasource

final class BehavioralRemoteDataSourceProvider
    extends
        $FunctionalProvider<
          BehavioralRemoteDataSource,
          BehavioralRemoteDataSource,
          BehavioralRemoteDataSource
        >
    with $Provider<BehavioralRemoteDataSource> {
  /// Provider for behavioral remote datasource
  const BehavioralRemoteDataSourceProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'behavioralRemoteDataSourceProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$behavioralRemoteDataSourceHash();

  @$internal
  @override
  $ProviderElement<BehavioralRemoteDataSource> $createElement(
    $ProviderPointer pointer,
  ) => $ProviderElement(pointer);

  @override
  BehavioralRemoteDataSource create(Ref ref) {
    return behavioralRemoteDataSource(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(BehavioralRemoteDataSource value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<BehavioralRemoteDataSource>(value),
    );
  }
}

String _$behavioralRemoteDataSourceHash() =>
    r'ef1e78f34b8996ca821f32c00e1c7ff6fc836b4c';

/// Provider for feedback state management

@ProviderFor(BehavioralFeedback)
const behavioralFeedbackProvider = BehavioralFeedbackProvider._();

/// Provider for feedback state management
final class BehavioralFeedbackProvider
    extends $NotifierProvider<BehavioralFeedback, FeedbackState> {
  /// Provider for feedback state management
  const BehavioralFeedbackProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'behavioralFeedbackProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$behavioralFeedbackHash();

  @$internal
  @override
  BehavioralFeedback create() => BehavioralFeedback();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(FeedbackState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<FeedbackState>(value),
    );
  }
}

String _$behavioralFeedbackHash() =>
    r'fa1c787868f20d9dffd7ede21a7faf26be6b7fc7';

/// Provider for feedback state management

abstract class _$BehavioralFeedback extends $Notifier<FeedbackState> {
  FeedbackState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<FeedbackState, FeedbackState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<FeedbackState, FeedbackState>,
              FeedbackState,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
