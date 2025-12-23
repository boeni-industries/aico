// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'proactive_providers.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Provider for ProactiveRemoteDataSource

@ProviderFor(proactiveRemoteDataSource)
const proactiveRemoteDataSourceProvider = ProactiveRemoteDataSourceProvider._();

/// Provider for ProactiveRemoteDataSource

final class ProactiveRemoteDataSourceProvider
    extends
        $FunctionalProvider<
          ProactiveRemoteDataSource,
          ProactiveRemoteDataSource,
          ProactiveRemoteDataSource
        >
    with $Provider<ProactiveRemoteDataSource> {
  /// Provider for ProactiveRemoteDataSource
  const ProactiveRemoteDataSourceProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'proactiveRemoteDataSourceProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$proactiveRemoteDataSourceHash();

  @$internal
  @override
  $ProviderElement<ProactiveRemoteDataSource> $createElement(
    $ProviderPointer pointer,
  ) => $ProviderElement(pointer);

  @override
  ProactiveRemoteDataSource create(Ref ref) {
    return proactiveRemoteDataSource(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ProactiveRemoteDataSource value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ProactiveRemoteDataSource>(value),
    );
  }
}

String _$proactiveRemoteDataSourceHash() =>
    r'f9725a06b59d295cf6dbef0c3f31d373b8b70855';

/// Provider for ProactiveRepository

@ProviderFor(proactiveRepository)
const proactiveRepositoryProvider = ProactiveRepositoryProvider._();

/// Provider for ProactiveRepository

final class ProactiveRepositoryProvider
    extends
        $FunctionalProvider<
          ProactiveRepository,
          ProactiveRepository,
          ProactiveRepository
        >
    with $Provider<ProactiveRepository> {
  /// Provider for ProactiveRepository
  const ProactiveRepositoryProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'proactiveRepositoryProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$proactiveRepositoryHash();

  @$internal
  @override
  $ProviderElement<ProactiveRepository> $createElement(
    $ProviderPointer pointer,
  ) => $ProviderElement(pointer);

  @override
  ProactiveRepository create(Ref ref) {
    return proactiveRepository(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ProactiveRepository value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ProactiveRepository>(value),
    );
  }
}

String _$proactiveRepositoryHash() =>
    r'068ce902beaddc9f16d43e61cde3311334def1ea';
