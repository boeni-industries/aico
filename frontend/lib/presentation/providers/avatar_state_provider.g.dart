// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'avatar_state_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Provider for avatar ring state

@ProviderFor(AvatarRingStateNotifier)
const avatarRingStateProvider = AvatarRingStateNotifierProvider._();

/// Provider for avatar ring state
final class AvatarRingStateNotifierProvider
    extends $NotifierProvider<AvatarRingStateNotifier, AvatarRingState> {
  /// Provider for avatar ring state
  const AvatarRingStateNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'avatarRingStateProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$avatarRingStateNotifierHash();

  @$internal
  @override
  AvatarRingStateNotifier create() => AvatarRingStateNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AvatarRingState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<AvatarRingState>(value),
    );
  }
}

String _$avatarRingStateNotifierHash() =>
    r'65a7d09c8001d4785125d589d044af941341ac93';

/// Provider for avatar ring state

abstract class _$AvatarRingStateNotifier extends $Notifier<AvatarRingState> {
  AvatarRingState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<AvatarRingState, AvatarRingState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AvatarRingState, AvatarRingState>,
              AvatarRingState,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
