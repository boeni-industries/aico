import 'package:equatable/equatable.dart';

/// Events for the Settings BLoC
/// Handles all settings-related actions and state transitions
abstract class SettingsEvent extends Equatable {
  const SettingsEvent();

  @override
  List<Object?> get props => [];
}

/// Load settings from storage
class SettingsLoad extends SettingsEvent {
  const SettingsLoad();
}

/// Update theme setting
class SettingsUpdateTheme extends SettingsEvent {
  final String theme;

  const SettingsUpdateTheme(this.theme);

  @override
  List<Object?> get props => [theme];
}

/// Update language setting
class SettingsUpdateLanguage extends SettingsEvent {
  final String language;

  const SettingsUpdateLanguage(this.language);

  @override
  List<Object?> get props => [language];
}

/// Update notifications setting
class SettingsUpdateNotifications extends SettingsEvent {
  final bool enabled;

  const SettingsUpdateNotifications(this.enabled);

  @override
  List<Object?> get props => [enabled];
}

/// Update auto-connect setting
class SettingsUpdateAutoConnect extends SettingsEvent {
  final bool enabled;

  const SettingsUpdateAutoConnect(this.enabled);

  @override
  List<Object?> get props => [enabled];
}

/// Update default server URL
class SettingsUpdateServerUrl extends SettingsEvent {
  final String serverUrl;

  const SettingsUpdateServerUrl(this.serverUrl);

  @override
  List<Object?> get props => [serverUrl];
}

/// Update custom setting
class SettingsUpdateCustom extends SettingsEvent {
  final String key;
  final dynamic value;

  const SettingsUpdateCustom(this.key, this.value);

  @override
  List<Object?> get props => [key, value];
}

/// Reset settings to defaults
class SettingsReset extends SettingsEvent {
  const SettingsReset();
}

/// Save current settings
class SettingsSave extends SettingsEvent {
  const SettingsSave();
}

/// Import settings from JSON
class SettingsImport extends SettingsEvent {
  final Map<String, dynamic> settingsData;

  const SettingsImport(this.settingsData);

  @override
  List<Object?> get props => [settingsData];
}

/// Export settings to JSON
class SettingsExport extends SettingsEvent {
  const SettingsExport();
}
