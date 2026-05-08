"""
Test descriptions for text model testing.
Contains descriptions and expected classifications.
"""

# Artificial test descriptions
ARTIFICIAL_TEST_DESCRIPTIONS = {
    "TC-11": {
        "text": "The lemon tree looks very healthy with vibrant green leaves, strong stems, and abundant fruit bearing. The foliage is dense and uniform without any visible spots or discoloration.",
        "expected_class": "Healthy",
        "data_type": "Artificial",
    },
    "TC-12": {
        "text": "The lemon tree exhibits classic witch broom disease symptoms. The branches show dense, abnormal growth patterns resembling a broom. The affected areas have twisted and distorted shoots with reduced fruit production.",
        "expected_class": "Witch Broom",
        "data_type": "Artificial",
    },
    "TC-13": {
        "text": "The lemon tree leaves show yellowing and mottling patterns characteristic of citrus greening disease. The leaves are asymmetrical and the tree shows signs of decline.",
        "expected_class": "Unknown",
        "data_type": "Artificial",
    },
}

# Available test descriptions (from websites/public sources)
AVAILABLE_TEST_DESCRIPTIONS = {
    "TC-14": {
        "text": "Healthy lemon plant leaves are typically smooth, dark green, and glossy. The petioles are winged, and the leaflets have finely serrated margins. Healthy trees produce abundant, regular fruiting.",
        "expected_class": "Healthy",
        "data_type": "Available",
    },
    "TC-15": {
        "text": "Witch broom is a serious disease of citrus characterized by abnormal bushy growth of branches. The affected branches show dense clustering of twigs and excessive branching, resembling a witch's broom.",
        "expected_class": "Witch Broom",
        "data_type": "Available",
    },
    "TC-16": {
        "text": "The lemon tree leaves display various symptoms of stress including brown spots, yellowing, wilting, and necrotic lesions. The overall health appears compromised.",
        "expected_class": "Unknown",
        "data_type": "Available",
    },
}

# Real test descriptions (personally generated)
REAL_TEST_DESCRIPTIONS = {
    "TC-17": {
        "text": "Our lemon tree in the backyard is doing well. The leaves are all green without any spots. The branches look normal and we are getting good production of lemons this season.",
        "expected_class": "Healthy",
        "data_type": "Real",
    },
    "TC-18": {
        "text": "One of our lemon trees has become problematic. The branches near the top have started showing excessive branching and twisted growth. They look like thick bunches of sticks all tangled together.",
        "expected_class": "Witch Broom",
        "data_type": "Real",
    },
    "TC-19": {
        "text": "The lemon tree has some weird looking leaves but I can't tell exactly what disease it is. The plant is still growing but doesn't look as vigorous as before.",
        "expected_class": "Unknown",
        "data_type": "Real",
    },
}

ALL_TEXT_DESCRIPTIONS = {
    **ARTIFICIAL_TEST_DESCRIPTIONS,
    **AVAILABLE_TEST_DESCRIPTIONS,
    **REAL_TEST_DESCRIPTIONS,
}


def get_test_description(test_case_id: str) -> dict:
    """Get test description for a given test case ID."""
    return ALL_TEXT_DESCRIPTIONS.get(test_case_id)


def get_all_text_test_inputs() -> dict[str, str]:
    """Get all text test inputs mapped by test case ID."""
    return {tc_id: data["text"] for tc_id, data in ALL_TEXT_DESCRIPTIONS.items()}
