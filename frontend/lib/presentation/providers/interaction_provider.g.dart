// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'interaction_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Main interaction state provider

@ProviderFor(Interaction)
const interactionProvider = InteractionProvider._();

/// Main interaction state provider
final class InteractionProvider
    extends $NotifierProvider<Interaction, InteractionState> {
  /// Main interaction state provider
  const InteractionProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'interactionProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$interactionHash();

  @$internal
  @override
  Interaction create() => Interaction();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(InteractionState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<InteractionState>(value),
    );
  }
}

String _$interactionHash() => r'782622d48cbb0621393fdf5b3c8d23f263854671';

/// Main interaction state provider

abstract class _$Interaction extends $Notifier<InteractionState> {
  InteractionState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<InteractionState, InteractionState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<InteractionState, InteractionState>,
              InteractionState,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
