// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'settings_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Settings provider using Notifier

@ProviderFor(SettingsNotifier)
const settingsProvider = SettingsNotifierProvider._();

/// Settings provider using Notifier
final class SettingsNotifierProvider
    extends $NotifierProvider<SettingsNotifier, SettingsState> {
  /// Settings provider using Notifier
  const SettingsNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'settingsProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$settingsNotifierHash();

  @$internal
  @override
  SettingsNotifier create() => SettingsNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(SettingsState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<SettingsState>(value),
    );
  }
}

String _$settingsNotifierHash() => r'05318b3bc9995e891bf0f856c5b26345c4c28384';

/// Settings provider using Notifier

abstract class _$SettingsNotifier extends $Notifier<SettingsState> {
  SettingsState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<SettingsState, SettingsState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<SettingsState, SettingsState>,
              SettingsState,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}

/// Theme mode provider (convenience)

@ProviderFor(themeMode)
const themeModeProvider = ThemeModeProvider._();

/// Theme mode provider (convenience)

final class ThemeModeProvider
    extends $FunctionalProvider<ThemeMode, ThemeMode, ThemeMode>
    with $Provider<ThemeMode> {
  /// Theme mode provider (convenience)
  const ThemeModeProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'themeModeProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$themeModeHash();

  @$internal
  @override
  $ProviderElement<ThemeMode> $createElement($ProviderPointer pointer) =>
      $ProviderElement(pointer);

  @override
  ThemeMode create(Ref ref) {
    return themeMode(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ThemeMode value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ThemeMode>(value),
    );
  }
}

String _$themeModeHash() => r'd604918e9656a71c55bba934001b634dba8de52a';

/// High contrast provider (convenience)

@ProviderFor(highContrast)
const highContrastProvider = HighContrastProvider._();

/// High contrast provider (convenience)

final class HighContrastProvider extends $FunctionalProvider<bool, bool, bool>
    with $Provider<bool> {
  /// High contrast provider (convenience)
  const HighContrastProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'highContrastProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$highContrastHash();

  @$internal
  @override
  $ProviderElement<bool> $createElement($ProviderPointer pointer) =>
      $ProviderElement(pointer);

  @override
  bool create(Ref ref) {
    return highContrast(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(bool value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<bool>(value),
    );
  }
}

String _$highContrastHash() => r'2f0842072b01f2b74b62e141e9cdb60e7ac72d60';
