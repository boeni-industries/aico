// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'layout_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Notifier class for layout state management

@ProviderFor(Layout)
const layoutProvider = LayoutProvider._();

/// Notifier class for layout state management
final class LayoutProvider extends $NotifierProvider<Layout, LayoutState> {
  /// Notifier class for layout state management
  const LayoutProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'layoutProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$layoutHash();

  @$internal
  @override
  Layout create() => Layout();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(LayoutState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<LayoutState>(value),
    );
  }
}

String _$layoutHash() => r'4f997f99dccf50a7be182f0af49d4246ee53ac52';

/// Notifier class for layout state management

abstract class _$Layout extends $Notifier<LayoutState> {
  LayoutState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<LayoutState, LayoutState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<LayoutState, LayoutState>,
              LayoutState,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
