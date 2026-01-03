// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'proactive_state_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Provider for proactive conversation state

@ProviderFor(ProactiveStateNotifier)
const proactiveStateProvider = ProactiveStateNotifierProvider._();

/// Provider for proactive conversation state
final class ProactiveStateNotifierProvider
    extends $NotifierProvider<ProactiveStateNotifier, ProactiveState> {
  /// Provider for proactive conversation state
  const ProactiveStateNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'proactiveStateProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$proactiveStateNotifierHash();

  @$internal
  @override
  ProactiveStateNotifier create() => ProactiveStateNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ProactiveState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ProactiveState>(value),
    );
  }
}

String _$proactiveStateNotifierHash() =>
    r'46228dead88a1a5448db51d15f95504dac9b6d33';

/// Provider for proactive conversation state

abstract class _$ProactiveStateNotifier extends $Notifier<ProactiveState> {
  ProactiveState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<ProactiveState, ProactiveState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<ProactiveState, ProactiveState>,
              ProactiveState,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
