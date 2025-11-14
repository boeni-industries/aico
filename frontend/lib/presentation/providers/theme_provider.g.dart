// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'theme_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Theme manager provider

@ProviderFor(themeManager)
const themeManagerProvider = ThemeManagerProvider._();

/// Theme manager provider

final class ThemeManagerProvider
    extends
        $FunctionalProvider<
          AicoThemeManager,
          AicoThemeManager,
          AicoThemeManager
        >
    with $Provider<AicoThemeManager> {
  /// Theme manager provider
  const ThemeManagerProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'themeManagerProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$themeManagerHash();

  @$internal
  @override
  $ProviderElement<AicoThemeManager> $createElement($ProviderPointer pointer) =>
      $ProviderElement(pointer);

  @override
  AicoThemeManager create(Ref ref) {
    return themeManager(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AicoThemeManager value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<AicoThemeManager>(value),
    );
  }
}

String _$themeManagerHash() => r'd186a2fe79d2c4aa5a21fa58c6b8c3db5a5ab0c0';

/// Current theme data provider

@ProviderFor(currentTheme)
const currentThemeProvider = CurrentThemeProvider._();

/// Current theme data provider

final class CurrentThemeProvider
    extends $FunctionalProvider<ThemeData, ThemeData, ThemeData>
    with $Provider<ThemeData> {
  /// Current theme data provider
  const CurrentThemeProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'currentThemeProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$currentThemeHash();

  @$internal
  @override
  $ProviderElement<ThemeData> $createElement($ProviderPointer pointer) =>
      $ProviderElement(pointer);

  @override
  ThemeData create(Ref ref) {
    return currentTheme(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ThemeData value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ThemeData>(value),
    );
  }
}

String _$currentThemeHash() => r'057be39d4eb064f51170cda211f0c6d1b6595396';

/// Light theme provider

@ProviderFor(lightTheme)
const lightThemeProvider = LightThemeProvider._();

/// Light theme provider

final class LightThemeProvider
    extends $FunctionalProvider<ThemeData, ThemeData, ThemeData>
    with $Provider<ThemeData> {
  /// Light theme provider
  const LightThemeProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'lightThemeProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$lightThemeHash();

  @$internal
  @override
  $ProviderElement<ThemeData> $createElement($ProviderPointer pointer) =>
      $ProviderElement(pointer);

  @override
  ThemeData create(Ref ref) {
    return lightTheme(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ThemeData value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ThemeData>(value),
    );
  }
}

String _$lightThemeHash() => r'4cbc34f81e080f7a8d37f082ba29139b5723a634';

/// Dark theme provider

@ProviderFor(darkTheme)
const darkThemeProvider = DarkThemeProvider._();

/// Dark theme provider

final class DarkThemeProvider
    extends $FunctionalProvider<ThemeData, ThemeData, ThemeData>
    with $Provider<ThemeData> {
  /// Dark theme provider
  const DarkThemeProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'darkThemeProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$darkThemeHash();

  @$internal
  @override
  $ProviderElement<ThemeData> $createElement($ProviderPointer pointer) =>
      $ProviderElement(pointer);

  @override
  ThemeData create(Ref ref) {
    return darkTheme(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ThemeData value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ThemeData>(value),
    );
  }
}

String _$darkThemeHash() => r'4a43b52fa9ff3e44d622ed0c7f7753fe48f98ea2';

/// High contrast light theme provider

@ProviderFor(highContrastLightTheme)
const highContrastLightThemeProvider = HighContrastLightThemeProvider._();

/// High contrast light theme provider

final class HighContrastLightThemeProvider
    extends $FunctionalProvider<ThemeData, ThemeData, ThemeData>
    with $Provider<ThemeData> {
  /// High contrast light theme provider
  const HighContrastLightThemeProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'highContrastLightThemeProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$highContrastLightThemeHash();

  @$internal
  @override
  $ProviderElement<ThemeData> $createElement($ProviderPointer pointer) =>
      $ProviderElement(pointer);

  @override
  ThemeData create(Ref ref) {
    return highContrastLightTheme(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ThemeData value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ThemeData>(value),
    );
  }
}

String _$highContrastLightThemeHash() =>
    r'28b826de2d49853b54d9cd00711df3a16851f6a8';

/// High contrast dark theme provider

@ProviderFor(highContrastDarkTheme)
const highContrastDarkThemeProvider = HighContrastDarkThemeProvider._();

/// High contrast dark theme provider

final class HighContrastDarkThemeProvider
    extends $FunctionalProvider<ThemeData, ThemeData, ThemeData>
    with $Provider<ThemeData> {
  /// High contrast dark theme provider
  const HighContrastDarkThemeProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'highContrastDarkThemeProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$highContrastDarkThemeHash();

  @$internal
  @override
  $ProviderElement<ThemeData> $createElement($ProviderPointer pointer) =>
      $ProviderElement(pointer);

  @override
  ThemeData create(Ref ref) {
    return highContrastDarkTheme(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ThemeData value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ThemeData>(value),
    );
  }
}

String _$highContrastDarkThemeHash() =>
    r'287ece027b186178d575f60f95a2baeedfddd3ea';

/// Theme controller for managing theme operations

@ProviderFor(ThemeController)
const themeControllerProvider = ThemeControllerProvider._();

/// Theme controller for managing theme operations
final class ThemeControllerProvider
    extends $NotifierProvider<ThemeController, ThemeState> {
  /// Theme controller for managing theme operations
  const ThemeControllerProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'themeControllerProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$themeControllerHash();

  @$internal
  @override
  ThemeController create() => ThemeController();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ThemeState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ThemeState>(value),
    );
  }
}

String _$themeControllerHash() => r'ff3f1a66090a193ea2c7f7a3786b50dbe6f12c1b';

/// Theme controller for managing theme operations

abstract class _$ThemeController extends $Notifier<ThemeState> {
  ThemeState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<ThemeState, ThemeState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<ThemeState, ThemeState>,
              ThemeState,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
