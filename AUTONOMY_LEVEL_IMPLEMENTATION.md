# Autonomy Level Implementation Guide

## Current Status

### ✅ Completed
1. **Database schema** - `autonomy_level` column exists
2. **Data models** - All models use `autonomy_level`
3. **Backend API** - GET/PUT endpoints work correctly
4. **Configuration hierarchy** - User DB value > Config default > Fallback

### ❌ Not Implemented Yet

#### 1. System Doesn't Respect autonomy_level
The `autonomy_level` is stored but **not checked** anywhere to control behavior.

#### 2. No Frontend UI
Users cannot edit their `autonomy_level` setting.

---

## Where autonomy_level Should Be Checked

### 1. Goal Activation (Arbiter)
**File**: `shared/aico/ai/agency/arbiter.py`
**Method**: `update_intention_set()`

**Current behavior**: Goals are activated automatically based on priority/score.

**Should check autonomy_level**:
```python
# In update_intention_set() before activating goals
profile = await self.values_ethics._get_or_create_profile(user_id, uow)

if profile.autonomy_level == AutonomyLevel.QUIET:
    # Don't auto-activate ANY goals - only user-explicit
    # Only activate goals with origin=USER
    if scored_goal.goal.origin != GoalOrigin.USER:
        continue  # Skip autonomous goals
        
elif profile.autonomy_level == AutonomyLevel.BALANCED:
    # Create goals but keep them PROPOSED (not ACTIVE)
    # Require user to manually activate
    intention = await self._create_intention(scored_goal, user_id, activate=False)
    
elif profile.autonomy_level == AutonomyLevel.PROACTIVE:
    # Auto-activate goals (current behavior)
    intention = await self._create_intention(scored_goal, user_id, activate=True)
    
elif profile.autonomy_level == AutonomyLevel.AUTONOMOUS:
    # Fully autonomous - activate everything within safety constraints
    intention = await self._create_intention(scored_goal, user_id, activate=True)
```

### 2. Proactive Conversations
**File**: `shared/aico/ai/agency/skills/communication/initiate.py`
**Method**: `execute()`

**Should check autonomy_level**:
```python
profile = await self.values_ethics._get_or_create_profile(user_id, uow)

if profile.autonomy_level == AutonomyLevel.QUIET:
    # Never initiate conversations
    return {"status": "blocked", "reason": "user_autonomy_level_quiet"}
    
elif profile.autonomy_level == AutonomyLevel.BALANCED:
    # Only initiate for high-priority items
    if priority < 0.8:
        return {"status": "blocked", "reason": "autonomy_level_requires_high_priority"}
```

### 3. Follow-ups and Reminders
**File**: `shared/aico/ai/agency/proactive.py`
**Method**: `generate_followup()`, `schedule_reminder()`

**Should check autonomy_level**:
```python
profile = await self.values_ethics._get_or_create_profile(user_id, uow)

if profile.autonomy_level == AutonomyLevel.QUIET:
    # No proactive follow-ups
    return None
    
elif profile.autonomy_level == AutonomyLevel.BALANCED:
    # Only critical follow-ups
    if followup_type != FollowupType.COMPLETION_PROMPT:
        return None
```

### 4. Curiosity-Driven Goals
**File**: `shared/aico/ai/curiosity/engine.py`
**Method**: Goal generation from curiosity signals

**Should check autonomy_level**:
```python
profile = await self.values_ethics._get_or_create_profile(user_id, uow)

if profile.autonomy_level == AutonomyLevel.QUIET:
    # No curiosity-driven goals
    return []
    
elif profile.autonomy_level == AutonomyLevel.BALANCED:
    # Create goals but mark as PROPOSED
    goal.status = GoalStatus.PROPOSED
```

---

## Frontend UI Implementation

### Option 1: Add to Settings Screen (Recommended)
**File**: `frontend/lib/presentation/screens/settings/settings_screen.dart`

Add a new section:
```dart
// Autonomy Level Setting
ListTile(
  title: Text('Autonomy Level'),
  subtitle: Text(_getAutonomyDescription(currentLevel)),
  trailing: DropdownButton<String>(
    value: currentLevel,
    items: [
      DropdownMenuItem(value: 'quiet', child: Text('Quiet')),
      DropdownMenuItem(value: 'balanced', child: Text('Balanced')),
      DropdownMenuItem(value: 'proactive', child: Text('Proactive')),
      DropdownMenuItem(value: 'autonomous', child: Text('Autonomous')),
    ],
    onChanged: (value) => _updateAutonomyLevel(value),
  ),
)
```

### Option 2: Add to Agency Page
Create a dedicated agency settings section where users can control:
- Autonomy level
- Curiosity intensity
- Sensitive life areas

---

## API Integration

### Frontend Service
Create or update agency service:

```dart
class AgencyService {
  Future<ValueProfile> getProfile() async {
    final response = await http.get('/api/v1/agency/profile');
    return ValueProfile.fromJson(response.data);
  }
  
  Future<ValueProfile> updateAutonomyLevel(String level) async {
    final response = await http.put(
      '/api/v1/agency/profile',
      data: {'autonomy_level': level},
    );
    return ValueProfile.fromJson(response.data);
  }
}
```

### State Management
Use Riverpod provider:

```dart
final autonomyLevelProvider = StateNotifierProvider<AutonomyLevelNotifier, String>((ref) {
  return AutonomyLevelNotifier(ref.read(agencyServiceProvider));
});

class AutonomyLevelNotifier extends StateNotifier<String> {
  final AgencyService _service;
  
  AutonomyLevelNotifier(this._service) : super('balanced') {
    _loadProfile();
  }
  
  Future<void> _loadProfile() async {
    final profile = await _service.getProfile();
    state = profile.autonomyLevel;
  }
  
  Future<void> update(String level) async {
    await _service.updateAutonomyLevel(level);
    state = level;
  }
}
```

---

## Testing Checklist

### Backend Tests
- [ ] Test autonomy_level=quiet blocks autonomous goals
- [ ] Test autonomy_level=balanced creates PROPOSED goals only
- [ ] Test autonomy_level=proactive auto-activates goals
- [ ] Test autonomy_level=autonomous allows full autonomy

### Frontend Tests
- [ ] Test UI displays current autonomy_level
- [ ] Test UI can update autonomy_level
- [ ] Test changes persist to database
- [ ] Test changes reflect in system behavior

### Integration Tests
- [ ] Create goal with autonomy_level=quiet → should not activate
- [ ] Create goal with autonomy_level=proactive → should activate
- [ ] Change autonomy_level → existing goals should respect new setting

---

## Implementation Priority

1. **High Priority** (Do First)
   - Add autonomy_level checks in Arbiter goal activation
   - Add frontend UI for editing autonomy_level
   
2. **Medium Priority**
   - Add checks in proactive conversation initiation
   - Add checks in follow-up generation
   
3. **Low Priority** (Future)
   - Add checks in curiosity-driven goal generation
   - Add advanced autonomy controls (per-domain settings)

---

## Configuration Descriptions

For UI display:

```dart
String _getAutonomyDescription(String level) {
  switch (level) {
    case 'quiet':
      return 'Only respond to explicit requests. No autonomous actions.';
    case 'balanced':
      return 'Create goals from curiosity but require your activation.';
    case 'proactive':
      return 'Autonomously activate goals and send occasional suggestions.';
    case 'autonomous':
      return 'Fully autonomous goal pursuit within safety constraints.';
    default:
      return '';
  }
}
```
