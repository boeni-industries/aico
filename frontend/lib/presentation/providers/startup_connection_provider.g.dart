// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'startup_connection_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(StartupConnectionNotifier)
const startupConnectionProvider = StartupConnectionNotifierProvider._();

final class StartupConnectionNotifierProvider
    extends
        $NotifierProvider<StartupConnectionNotifier, StartupConnectionState> {
  const StartupConnectionNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'startupConnectionProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$startupConnectionNotifierHash();

  @$internal
  @override
  StartupConnectionNotifier create() => StartupConnectionNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(StartupConnectionState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<StartupConnectionState>(value),
    );
  }
}

String _$startupConnectionNotifierHash() =>
    r'a6a217048ad8a9d6d09aff402653a3dcae03d41a';

abstract class _$StartupConnectionNotifier
    extends $Notifier<StartupConnectionState> {
  StartupConnectionState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref =
        this.ref as $Ref<StartupConnectionState, StartupConnectionState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<StartupConnectionState, StartupConnectionState>,
              StartupConnectionState,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
