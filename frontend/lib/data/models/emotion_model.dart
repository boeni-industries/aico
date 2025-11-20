import 'package:json_annotation/json_annotation.dart';

part 'emotion_model.g.dart';

/// Emotion state model matching backend API response
@JsonSerializable()
class EmotionModel {
  final String timestamp;
  final String primary;
  final double confidence;
  final double valence;
  final double arousal;
  final double dominance;

  EmotionModel({
    required this.timestamp,
    required this.primary,
    required this.confidence,
    required this.valence,
    required this.arousal,
    required this.dominance,
  });

  factory EmotionModel.fromJson(Map<String, dynamic> json) =>
      _$EmotionModelFromJson(json);

  Map<String, dynamic> toJson() => _$EmotionModelToJson(this);
}

/// Emotion history item
@JsonSerializable()
class EmotionHistoryItem {
  final String timestamp;
  final String feeling;
  final double valence;
  final double arousal;
  final double intensity;

  EmotionHistoryItem({
    required this.timestamp,
    required this.feeling,
    required this.valence,
    required this.arousal,
    required this.intensity,
  });

  factory EmotionHistoryItem.fromJson(Map<String, dynamic> json) =>
      _$EmotionHistoryItemFromJson(json);

  Map<String, dynamic> toJson() => _$EmotionHistoryItemToJson(this);
}
