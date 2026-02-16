// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'agency_state_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Provider for agency badge state

@ProviderFor(AgencyBadgeStateNotifier)
const agencyBadgeStateProvider = AgencyBadgeStateNotifierProvider._();

/// Provider for agency badge state
final class AgencyBadgeStateNotifierProvider
    extends $NotifierProvider<AgencyBadgeStateNotifier, AgencyBadgeState> {
  /// Provider for agency badge state
  const AgencyBadgeStateNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'agencyBadgeStateProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$agencyBadgeStateNotifierHash();

  @$internal
  @override
  AgencyBadgeStateNotifier create() => AgencyBadgeStateNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AgencyBadgeState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<AgencyBadgeState>(value),
    );
  }
}

String _$agencyBadgeStateNotifierHash() =>
    r'9574176163d8b4374da419d89f2da20907ae6768';

/// Provider for agency badge state

abstract class _$AgencyBadgeStateNotifier extends $Notifier<AgencyBadgeState> {
  AgencyBadgeState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<AgencyBadgeState, AgencyBadgeState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AgencyBadgeState, AgencyBadgeState>,
              AgencyBadgeState,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
