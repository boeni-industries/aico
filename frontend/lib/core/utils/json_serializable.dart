import 'dart:convert';

/// Generic JSON serialization mixin with error handling
/// Provides consistent serialization patterns across all state classes
mixin JsonSerializable<T> {
  /// Convert object to JSON map
  Map<String, dynamic> toJson();

  /// Create object from JSON map
  T fromJson(Map<String, dynamic> json);

  /// Create a copy with modified fields
  T copyWith();

  /// Safe JSON encoding with error handling
  String toJsonString() {
    try {
      return jsonEncode(toJson());
    } catch (e) {
      throw SerializationException('Failed to encode JSON: $e');
    }
  }

  /// Safe JSON decoding with error handling
  static T fromJsonString<T extends JsonSerializable>(
    String jsonString,
    T Function(Map<String, dynamic>) fromJsonFactory,
  ) {
    try {
      final Map<String, dynamic> json = jsonDecode(jsonString);
      return fromJsonFactory(json);
    } catch (e) {
      throw SerializationException('Failed to decode JSON: $e');
    }
  }

  /// Validate required fields in JSON
  static void validateRequiredFields(
    Map<String, dynamic> json,
    List<String> requiredFields,
  ) {
    for (final field in requiredFields) {
      if (!json.containsKey(field)) {
        throw SerializationException('Missing required field: $field');
      }
    }
  }

  /// Safe field extraction with type checking
  static T getField<T>(
    Map<String, dynamic> json,
    String fieldName, {
    T? defaultValue,
  }) {
    final value = json[fieldName];
    if (value == null) {
      if (defaultValue != null) return defaultValue;
      throw SerializationException('Missing field: $fieldName');
    }
    if (value is! T) {
      throw SerializationException(
        'Field $fieldName expected type $T, got ${value.runtimeType}',
      );
    }
    return value;
  }
}

/// Custom exception for serialization errors
class SerializationException implements Exception {
  final String message;
  const SerializationException(this.message);

  @override
  String toString() => 'SerializationException: $message';
}
