// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'emotion_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

EmotionModel _$EmotionModelFromJson(Map<String, dynamic> json) => EmotionModel(
  timestamp: json['timestamp'] as String,
  primary: json['primary'] as String,
  confidence: (json['confidence'] as num).toDouble(),
  valence: (json['valence'] as num).toDouble(),
  arousal: (json['arousal'] as num).toDouble(),
  dominance: (json['dominance'] as num).toDouble(),
);

Map<String, dynamic> _$EmotionModelToJson(EmotionModel instance) =>
    <String, dynamic>{
      'timestamp': instance.timestamp,
      'primary': instance.primary,
      'confidence': instance.confidence,
      'valence': instance.valence,
      'arousal': instance.arousal,
      'dominance': instance.dominance,
    };

EmotionHistoryItem _$EmotionHistoryItemFromJson(Map<String, dynamic> json) =>
    EmotionHistoryItem(
      timestamp: json['timestamp'] as String,
      feeling: json['feeling'] as String,
      valence: (json['valence'] as num).toDouble(),
      arousal: (json['arousal'] as num).toDouble(),
      intensity: (json['intensity'] as num).toDouble(),
    );

Map<String, dynamic> _$EmotionHistoryItemToJson(EmotionHistoryItem instance) =>
    <String, dynamic>{
      'timestamp': instance.timestamp,
      'feeling': instance.feeling,
      'valence': instance.valence,
      'arousal': instance.arousal,
      'intensity': instance.intensity,
    };
