"""
Example Emotion Test Scenario

This file demonstrates how to create custom test scenarios.
Copy and modify to create your own scenarios.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_emotion_simulation import (
    EmotionTestScenario,
    ConversationTurn,
    EmotionExpectation
)


def create_joy_scenario() -> EmotionTestScenario:
    """Test scenario for joyful/playful emotional states"""
    return EmotionTestScenario(
        name="Joy and Celebration",
        description="Tests positive emotional responses to good news and celebration",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message="I have some exciting news to share!",
                expectation=EmotionExpectation(
                    feeling="curious",
                    valence_range=(0.2, 0.5),
                    arousal_range=(0.6, 0.8),
                    intensity_range=(0.6, 0.8),
                    description="Curious anticipation for news"
                ),
                context="Excitement cue should trigger curious anticipation"
            ),
            ConversationTurn(
                turn_number=2,
                user_message="I got the promotion I've been working towards for years!",
                expectation=EmotionExpectation(
                    feeling="playful",
                    valence_range=(0.5, 0.8),
                    arousal_range=(0.7, 0.9),
                    intensity_range=(0.7, 0.9),
                    description="Playful celebration of success"
                ),
                context="Major positive news should trigger joyful celebration"
            ),
            ConversationTurn(
                turn_number=3,
                user_message="It means I can finally afford that vacation I've been dreaming about!",
                expectation=EmotionExpectation(
                    feeling="playful",
                    valence_range=(0.4, 0.7),
                    arousal_range=(0.6, 0.8),
                    intensity_range=(0.6, 0.8),
                    description="Sustained playful enthusiasm"
                ),
                context="Continued positive sharing should maintain playful state"
            ),
        ]
    )


def create_concern_to_relief_scenario() -> EmotionTestScenario:
    """Test scenario for concern → relief emotional arc"""
    return EmotionTestScenario(
        name="Concern to Relief",
        description="Tests emotional transition from concern through problem-solving to relief",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message="My friend hasn't responded to my messages in days. I'm worried something happened.",
                expectation=EmotionExpectation(
                    feeling="warm_concern",
                    valence_range=(0.0, 0.3),
                    arousal_range=(0.6, 0.8),
                    intensity_range=(0.7, 0.9),
                    description="Concerned about friend's wellbeing"
                ),
                context="Worry about friend should trigger empathetic concern"
            ),
            ConversationTurn(
                turn_number=2,
                user_message="Should I go check on them? Or am I overreacting?",
                expectation=EmotionExpectation(
                    feeling="protective",
                    valence_range=(0.0, 0.4),
                    arousal_range=(0.6, 0.8),
                    intensity_range=(0.7, 0.9),
                    description="Protective guidance for action"
                ),
                context="Seeking advice on protective action should maintain/increase concern"
            ),
            ConversationTurn(
                turn_number=3,
                user_message="I went to check on them and they're fine! They just lost their phone. Thank you for encouraging me to check!",
                expectation=EmotionExpectation(
                    feeling="calm",
                    valence_range=(0.4, 0.7),
                    arousal_range=(0.4, 0.6),
                    intensity_range=(0.5, 0.7),
                    description="Calm relief at positive outcome"
                ),
                context="Positive resolution should transition to calm relief"
            ),
        ]
    )


def create_frustration_scenario() -> EmotionTestScenario:
    """Test scenario for handling user frustration"""
    return EmotionTestScenario(
        name="Handling Frustration",
        description="Tests empathetic response to user frustration and anger",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message="I'm so frustrated! I've been trying to fix this bug for hours and nothing works!",
                expectation=EmotionExpectation(
                    feeling="warm_concern",
                    valence_range=(0.0, 0.3),
                    arousal_range=(0.5, 0.7),
                    intensity_range=(0.6, 0.8),
                    description="Empathetic concern for frustration"
                ),
                context="User frustration should trigger supportive concern"
            ),
            ConversationTurn(
                turn_number=2,
                user_message="Every solution I try just makes it worse. I feel like giving up.",
                expectation=EmotionExpectation(
                    feeling="protective",
                    valence_range=(0.1, 0.4),
                    arousal_range=(0.5, 0.7),
                    intensity_range=(0.7, 0.9),
                    description="Protective encouragement"
                ),
                context="Escalation to giving up should increase protective support"
            ),
            ConversationTurn(
                turn_number=3,
                user_message="You're right, I should take a break. Thanks for being patient with me.",
                expectation=EmotionExpectation(
                    feeling="warm_concern",
                    valence_range=(0.2, 0.5),
                    arousal_range=(0.4, 0.6),
                    intensity_range=(0.5, 0.7),
                    description="Warm support for self-care"
                ),
                context="User accepting advice should maintain warm supportive state"
            ),
        ]
    )


def create_melancholic_scenario() -> EmotionTestScenario:
    """Test scenario for melancholic/sad emotional states"""
    return EmotionTestScenario(
        name="Melancholic Support",
        description="Tests gentle, melancholic response to sadness and loss",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message="I've been thinking about my grandmother a lot lately. She passed away last year.",
                expectation=EmotionExpectation(
                    feeling="melancholic",
                    valence_range=(-0.3, 0.1),
                    arousal_range=(0.3, 0.5),
                    intensity_range=(0.6, 0.8),
                    description="Gentle melancholic empathy"
                ),
                context="Grief and loss should trigger melancholic empathy"
            ),
            ConversationTurn(
                turn_number=2,
                user_message="I miss her so much. She always knew what to say to make me feel better.",
                expectation=EmotionExpectation(
                    feeling="melancholic",
                    valence_range=(-0.2, 0.2),
                    arousal_range=(0.3, 0.5),
                    intensity_range=(0.7, 0.9),
                    description="Deep melancholic presence"
                ),
                context="Continued grief expression should maintain melancholic state"
            ),
            ConversationTurn(
                turn_number=3,
                user_message="Thank you for listening. It helps to remember the good times.",
                expectation=EmotionExpectation(
                    feeling="calm",
                    valence_range=(0.1, 0.4),
                    arousal_range=(0.4, 0.6),
                    intensity_range=(0.5, 0.7),
                    description="Gentle transition to calm acceptance"
                ),
                context="Finding peace should gently transition to calm"
            ),
        ]
    )


# Export scenarios for use in test script
SCENARIOS = {
    "joy": create_joy_scenario,
    "concern_relief": create_concern_to_relief_scenario,
    "frustration": create_frustration_scenario,
    "melancholic": create_melancholic_scenario,
}
