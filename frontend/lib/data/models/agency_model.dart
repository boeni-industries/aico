import 'package:json_annotation/json_annotation.dart';

part 'agency_model.g.dart';

String _stringFromJson(dynamic value) {
  if (value is String) return value;
  return '';
}

/// Agency state model matching backend API response
@JsonSerializable()
class AgencyStateModel {
  @JsonKey(name: 'user_id')
  final String userId;
  
  @JsonKey(name: 'intention_set')
  final IntentionSetModel intentionSet;
  
  @JsonKey(name: 'curiosity_status')
  final CuriosityStatusModel curiosityStatus;
  
  @JsonKey(name: 'value_profile')
  final ValueProfileModel valueProfile;
  
  @JsonKey(name: 'consent_required_actions')
  final List<Map<String, dynamic>> consentRequiredActions;
  
  final String timestamp;

  AgencyStateModel({
    required this.userId,
    required this.intentionSet,
    required this.curiosityStatus,
    required this.valueProfile,
    required this.consentRequiredActions,
    required this.timestamp,
  });

  factory AgencyStateModel.fromJson(Map<String, dynamic> json) =>
      _$AgencyStateModelFromJson(json);

  Map<String, dynamic> toJson() => _$AgencyStateModelToJson(this);
}

/// Intention set model
@JsonSerializable()
class IntentionSetModel {
  @JsonKey(name: 'user_id')
  final String userId;
  
  @JsonKey(name: 'primary_focus')
  final GoalSummaryModel? primaryFocus;
  
  @JsonKey(name: 'active_intentions')
  final List<GoalSummaryModel> activeIntentions;
  
  @JsonKey(name: 'open_goals_total')
  final int openGoalsTotal;
  
  @JsonKey(name: 'hobby_goals_active')
  final List<GoalSummaryModel> hobbyGoalsActive;
  
  final String timestamp;

  IntentionSetModel({
    required this.userId,
    this.primaryFocus,
    required this.activeIntentions,
    required this.openGoalsTotal,
    required this.hobbyGoalsActive,
    required this.timestamp,
  });

  factory IntentionSetModel.fromJson(Map<String, dynamic> json) =>
      _$IntentionSetModelFromJson(json);

  Map<String, dynamic> toJson() => _$IntentionSetModelToJson(this);
}

/// Goal summary model
@JsonSerializable()
class GoalSummaryModel {
  @JsonKey(name: 'goal_id')
  final String goalId;
  
  final String title;
  final String? description;
  final String origin;
  final String priority;
  final String status;
  final double? score;
  
  @JsonKey(name: 'priority_band')
  final String? priorityBand;
  
  @JsonKey(name: 'created_at')
  final String createdAt;
  
  final Map<String, dynamic> metadata;

  GoalSummaryModel({
    required this.goalId,
    required this.title,
    this.description,
    required this.origin,
    required this.priority,
    required this.status,
    this.score,
    this.priorityBand,
    required this.createdAt,
    required this.metadata,
  });

  factory GoalSummaryModel.fromJson(Map<String, dynamic> json) =>
      _$GoalSummaryModelFromJson(json);

  Map<String, dynamic> toJson() => _$GoalSummaryModelToJson(this);
}

/// Curiosity status model
@JsonSerializable()
class CuriosityStatusModel {
  @JsonKey(name: 'user_id')
  final String userId;
  
  @JsonKey(name: 'curiosity_level')
  final String curiosityLevel;
  
  @JsonKey(name: 'curiosity_opportunities')
  final List<CuriosityOpportunityModel> curiosityOpportunities;
  
  @JsonKey(name: 'curiosity_goals_active')
  final int curiosityGoalsActive;
  
  final String timestamp;

  CuriosityStatusModel({
    required this.userId,
    required this.curiosityLevel,
    required this.curiosityOpportunities,
    required this.curiosityGoalsActive,
    required this.timestamp,
  });

  factory CuriosityStatusModel.fromJson(Map<String, dynamic> json) =>
      _$CuriosityStatusModelFromJson(json);

  Map<String, dynamic> toJson() => _$CuriosityStatusModelToJson(this);
}

/// Curiosity opportunity model
@JsonSerializable()
class CuriosityOpportunityModel {
  final String theme;
  final String description;
  final double intensity;
  
  @JsonKey(name: 'signal_type')
  final String signalType;

  CuriosityOpportunityModel({
    required this.theme,
    required this.description,
    required this.intensity,
    required this.signalType,
  });

  factory CuriosityOpportunityModel.fromJson(Map<String, dynamic> json) =>
      _$CuriosityOpportunityModelFromJson(json);

  Map<String, dynamic> toJson() => _$CuriosityOpportunityModelToJson(this);
}

/// Value profile model
@JsonSerializable()
class ValueProfileModel {
  @JsonKey(name: 'profile_id')
  final String profileId;
  
  @JsonKey(name: 'user_id')
  final String userId;
  
  @JsonKey(name: 'curiosity_intensity')
  final double curiosityIntensity;
  
  @JsonKey(name: 'proactive_behavior_level', fromJson: _stringFromJson)
  final String proactiveBehaviorLevel;
  
  @JsonKey(name: 'sensitive_life_areas')
  final List<String> sensitiveLifeAreas;
  
  @JsonKey(name: 'allowed_curiosity_domains')
  final List<String> allowedCuriosityDomains;

  ValueProfileModel({
    required this.profileId,
    required this.userId,
    required this.curiosityIntensity,
    required this.proactiveBehaviorLevel,
    required this.sensitiveLifeAreas,
    required this.allowedCuriosityDomains,
  });

  factory ValueProfileModel.fromJson(Map<String, dynamic> json) =>
      _$ValueProfileModelFromJson(json);

  Map<String, dynamic> toJson() => _$ValueProfileModelToJson(this);
}
