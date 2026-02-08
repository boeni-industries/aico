// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'agency_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

AgencyStateModel _$AgencyStateModelFromJson(Map<String, dynamic> json) =>
    AgencyStateModel(
      userId: json['user_id'] as String,
      intentionSet: IntentionSetModel.fromJson(
        json['intention_set'] as Map<String, dynamic>,
      ),
      curiosityStatus: CuriosityStatusModel.fromJson(
        json['curiosity_status'] as Map<String, dynamic>,
      ),
      valueProfile: ValueProfileModel.fromJson(
        json['value_profile'] as Map<String, dynamic>,
      ),
      consentRequiredActions:
          (json['consent_required_actions'] as List<dynamic>)
              .map((e) => e as Map<String, dynamic>)
              .toList(),
      timestamp: json['timestamp'] as String,
    );

Map<String, dynamic> _$AgencyStateModelToJson(AgencyStateModel instance) =>
    <String, dynamic>{
      'user_id': instance.userId,
      'intention_set': instance.intentionSet,
      'curiosity_status': instance.curiosityStatus,
      'value_profile': instance.valueProfile,
      'consent_required_actions': instance.consentRequiredActions,
      'timestamp': instance.timestamp,
    };

IntentionSetModel _$IntentionSetModelFromJson(Map<String, dynamic> json) =>
    IntentionSetModel(
      userId: json['user_id'] as String,
      primaryFocus: json['primary_focus'] == null
          ? null
          : GoalSummaryModel.fromJson(
              json['primary_focus'] as Map<String, dynamic>,
            ),
      activeIntentions: (json['active_intentions'] as List<dynamic>)
          .map((e) => GoalSummaryModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      openGoalsTotal: (json['open_goals_total'] as num).toInt(),
      hobbyGoalsActive: (json['hobby_goals_active'] as List<dynamic>)
          .map((e) => GoalSummaryModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      timestamp: json['timestamp'] as String,
    );

Map<String, dynamic> _$IntentionSetModelToJson(IntentionSetModel instance) =>
    <String, dynamic>{
      'user_id': instance.userId,
      'primary_focus': instance.primaryFocus,
      'active_intentions': instance.activeIntentions,
      'open_goals_total': instance.openGoalsTotal,
      'hobby_goals_active': instance.hobbyGoalsActive,
      'timestamp': instance.timestamp,
    };

GoalSummaryModel _$GoalSummaryModelFromJson(Map<String, dynamic> json) =>
    GoalSummaryModel(
      goalId: json['goal_id'] as String,
      title: json['title'] as String,
      description: json['description'] as String?,
      origin: json['origin'] as String,
      priority: json['priority'] as String,
      status: json['status'] as String,
      score: (json['score'] as num?)?.toDouble(),
      priorityBand: json['priority_band'] as String?,
      createdAt: json['created_at'] as String,
      metadata: json['metadata'] as Map<String, dynamic>,
    );

Map<String, dynamic> _$GoalSummaryModelToJson(GoalSummaryModel instance) =>
    <String, dynamic>{
      'goal_id': instance.goalId,
      'title': instance.title,
      'description': instance.description,
      'origin': instance.origin,
      'priority': instance.priority,
      'status': instance.status,
      'score': instance.score,
      'priority_band': instance.priorityBand,
      'created_at': instance.createdAt,
      'metadata': instance.metadata,
    };

CuriosityStatusModel _$CuriosityStatusModelFromJson(
  Map<String, dynamic> json,
) => CuriosityStatusModel(
  userId: json['user_id'] as String,
  curiosityLevel: json['curiosity_level'] as String,
  curiosityOpportunities: (json['curiosity_opportunities'] as List<dynamic>)
      .map((e) => CuriosityOpportunityModel.fromJson(e as Map<String, dynamic>))
      .toList(),
  curiosityGoalsActive: (json['curiosity_goals_active'] as num).toInt(),
  timestamp: json['timestamp'] as String,
);

Map<String, dynamic> _$CuriosityStatusModelToJson(
  CuriosityStatusModel instance,
) => <String, dynamic>{
  'user_id': instance.userId,
  'curiosity_level': instance.curiosityLevel,
  'curiosity_opportunities': instance.curiosityOpportunities,
  'curiosity_goals_active': instance.curiosityGoalsActive,
  'timestamp': instance.timestamp,
};

CuriosityOpportunityModel _$CuriosityOpportunityModelFromJson(
  Map<String, dynamic> json,
) => CuriosityOpportunityModel(
  theme: json['theme'] as String,
  description: json['description'] as String,
  intensity: (json['intensity'] as num).toDouble(),
  signalType: json['signal_type'] as String,
);

Map<String, dynamic> _$CuriosityOpportunityModelToJson(
  CuriosityOpportunityModel instance,
) => <String, dynamic>{
  'theme': instance.theme,
  'description': instance.description,
  'intensity': instance.intensity,
  'signal_type': instance.signalType,
};

ValueProfileModel _$ValueProfileModelFromJson(Map<String, dynamic> json) =>
    ValueProfileModel(
      profileId: json['profile_id'] as String,
      userId: json['user_id'] as String,
      curiosityIntensity: (json['curiosity_intensity'] as num).toDouble(),
      proactiveBehaviorLevel: _stringFromJson(json['proactive_behavior_level']),
      sensitiveLifeAreas: (json['sensitive_life_areas'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      allowedCuriosityDomains:
          (json['allowed_curiosity_domains'] as List<dynamic>)
              .map((e) => e as String)
              .toList(),
    );

Map<String, dynamic> _$ValueProfileModelToJson(ValueProfileModel instance) =>
    <String, dynamic>{
      'profile_id': instance.profileId,
      'user_id': instance.userId,
      'curiosity_intensity': instance.curiosityIntensity,
      'proactive_behavior_level': instance.proactiveBehaviorLevel,
      'sensitive_life_areas': instance.sensitiveLifeAreas,
      'allowed_curiosity_domains': instance.allowedCuriosityDomains,
    };
