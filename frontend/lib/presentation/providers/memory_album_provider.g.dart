// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'memory_album_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Provider for Memory Album repository

@ProviderFor(memoryAlbumRepository)
const memoryAlbumRepositoryProvider = MemoryAlbumRepositoryProvider._();

/// Provider for Memory Album repository

final class MemoryAlbumRepositoryProvider
    extends
        $FunctionalProvider<
          MemoryAlbumRepository,
          MemoryAlbumRepository,
          MemoryAlbumRepository
        >
    with $Provider<MemoryAlbumRepository> {
  /// Provider for Memory Album repository
  const MemoryAlbumRepositoryProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'memoryAlbumRepositoryProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$memoryAlbumRepositoryHash();

  @$internal
  @override
  $ProviderElement<MemoryAlbumRepository> $createElement(
    $ProviderPointer pointer,
  ) => $ProviderElement(pointer);

  @override
  MemoryAlbumRepository create(Ref ref) {
    return memoryAlbumRepository(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(MemoryAlbumRepository value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<MemoryAlbumRepository>(value),
    );
  }
}

String _$memoryAlbumRepositoryHash() =>
    r'6bc849512c544343495e9163cfac60330c677225';

/// Notifier for managing memories

@ProviderFor(MemoryAlbumNotifier)
const memoryAlbumProvider = MemoryAlbumNotifierProvider._();

/// Notifier for managing memories
final class MemoryAlbumNotifierProvider
    extends $NotifierProvider<MemoryAlbumNotifier, MemoriesState> {
  /// Notifier for managing memories
  const MemoryAlbumNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'memoryAlbumProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$memoryAlbumNotifierHash();

  @$internal
  @override
  MemoryAlbumNotifier create() => MemoryAlbumNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(MemoriesState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<MemoriesState>(value),
    );
  }
}

String _$memoryAlbumNotifierHash() =>
    r'8a75e928f95e262d4667359b1028375ca79fef9e';

/// Notifier for managing memories

abstract class _$MemoryAlbumNotifier extends $Notifier<MemoriesState> {
  MemoriesState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<MemoriesState, MemoriesState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<MemoriesState, MemoriesState>,
              MemoriesState,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
