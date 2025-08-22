import 'package:equatable/equatable.dart';
import '../../../core/utils/json_serializable.dart';

/// Settings state for the AICO app
/// Tracks user preferences and app configuration
abstract class SettingsState extends Equatable with JsonSerializable<SettingsState> {
  const SettingsState();

  @override
  List<Object?> get props => [];
}

/// Initial settings state
class SettingsInitial extends SettingsState {
  const SettingsInitial();

  @override
  Map<String, dynamic> toJson() => {'type': 'initial'};

  @override
  SettingsState fromJson(Map<String, dynamic> json) => const SettingsInitial();

  @override
  SettingsState copyWith() => const SettingsInitial();
}

/// Settings loading state
class SettingsLoading extends SettingsState {
  const SettingsLoading();

  @override
  Map<String, dynamic> toJson() => {'type': 'loading'};

  @override
  SettingsState fromJson(Map<String, dynamic> json) => const SettingsLoading();

  @override
  SettingsState copyWith() => const SettingsLoading();
}

/// Settings loaded successfully
class SettingsLoaded extends SettingsState {
  final AppSettings settings;

  const SettingsLoaded({required this.settings});

  @override
  List<Object?> get props => [settings];

  @override
  Map<String, dynamic> toJson() => {
    'type': 'loaded',
    'settings': settings.toJson(),
  };

  @override
  SettingsState fromJson(Map<String, dynamic> json) {
    JsonSerializable.validateRequiredFields(json, ['settings']);
    
    return SettingsLoaded(
      settings: AppSettings.fromJson(
        JsonSerializable.getField<Map<String, dynamic>>(json, 'settings'),
      ),
    );
  }

  @override
  SettingsState copyWith({AppSettings? settings}) {
    return SettingsLoaded(
      settings: settings ?? this.settings,
    );
  }
}

/// Settings error state
class SettingsError extends SettingsState {
  final String message;
  final DateTime occurredAt;

  const SettingsError({
    required this.message,
    required this.occurredAt,
  });

  @override
  List<Object?> get props => [message, occurredAt];

  @override
  Map<String, dynamic> toJson() => {
    'type': 'error',
    'message': message,
    'occurredAt': occurredAt.toIso8601String(),
  };

  @override
  SettingsState fromJson(Map<String, dynamic> json) {
    JsonSerializable.validateRequiredFields(json, ['message', 'occurredAt']);
    
    return SettingsError(
      message: JsonSerializable.getField<String>(json, 'message'),
      occurredAt: DateTime.parse(JsonSerializable.getField<String>(json, 'occurredAt')),
    );
  }

  @override
  SettingsState copyWith({
    String? message,
    DateTime? occurredAt,
  }) {
    return SettingsError(
      message: message ?? this.message,
      occurredAt: occurredAt ?? this.occurredAt,
    );
  }
}

/// App settings model
class AppSettings {
  final String theme;
  final String language;
  final bool notificationsEnabled;
  final bool autoConnect;
  final String defaultServerUrl;
  final Map<String, dynamic> customSettings;

  const AppSettings({
    this.theme = 'system',
    this.language = 'en',
    this.notificationsEnabled = true,
    this.autoConnect = true,
    this.defaultServerUrl = 'http://localhost:8000',
    this.customSettings = const {},
  });

  Map<String, dynamic> toJson() => {
    'theme': theme,
    'language': language,
    'notificationsEnabled': notificationsEnabled,
    'autoConnect': autoConnect,
    'defaultServerUrl': defaultServerUrl,
    'customSettings': customSettings,
  };

  factory AppSettings.fromJson(Map<String, dynamic> json) {
    return AppSettings(
      theme: json['theme'] as String? ?? 'system',
      language: json['language'] as String? ?? 'en',
      notificationsEnabled: json['notificationsEnabled'] as bool? ?? true,
      autoConnect: json['autoConnect'] as bool? ?? true,
      defaultServerUrl: json['defaultServerUrl'] as String? ?? 'http://localhost:8000',
      customSettings: json['customSettings'] as Map<String, dynamic>? ?? {},
    );
  }

  AppSettings copyWith({
    String? theme,
    String? language,
    bool? notificationsEnabled,
    bool? autoConnect,
    String? defaultServerUrl,
    Map<String, dynamic>? customSettings,
  }) {
    return AppSettings(
      theme: theme ?? this.theme,
      language: language ?? this.language,
      notificationsEnabled: notificationsEnabled ?? this.notificationsEnabled,
      autoConnect: autoConnect ?? this.autoConnect,
      defaultServerUrl: defaultServerUrl ?? this.defaultServerUrl,
      customSettings: customSettings ?? this.customSettings,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is AppSettings &&
        other.theme == theme &&
        other.language == language &&
        other.notificationsEnabled == notificationsEnabled &&
        other.autoConnect == autoConnect &&
        other.defaultServerUrl == defaultServerUrl &&
        _mapEquals(other.customSettings, customSettings);
  }

  @override
  int get hashCode {
    return Object.hash(
      theme,
      language,
      notificationsEnabled,
      autoConnect,
      defaultServerUrl,
      customSettings,
    );
  }

  bool _mapEquals(Map<String, dynamic> a, Map<String, dynamic> b) {
    if (a.length != b.length) return false;
    for (final key in a.keys) {
      if (!b.containsKey(key) || a[key] != b[key]) return false;
    }
    return true;
  }
}
