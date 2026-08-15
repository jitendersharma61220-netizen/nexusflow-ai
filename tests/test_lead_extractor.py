from unittest.mock import MagicMock

from agents.lead_extractor import LeadData, LeadExtractor
from llm.base import LLMUnavailableError


def _make_llm(chat_json_side_effect):
    llm = MagicMock()
    llm.is_available = True
    llm.chat_json.side_effect = chat_json_side_effect
    return llm


def test_extract_valid_json_updates_lead():
    valid_json = (
        '{"name": "Rahul", "phone": "9876543210", "budget": "1.5 Cr", "property_type": null, '
        '"configuration": "2 BHK", "preferred_location": "Golf Course Road", "purpose": "self-use", '
        '"purchase_timeline": "immediate", "requirements": null, "intent_score": 0, '
        '"lead_status": "cold", "ready_for_visit": false}'
    )
    llm = _make_llm([valid_json])
    extractor = LeadExtractor(llm)

    result = extractor.extract([{"role": "user", "content": "hi"}], LeadData())

    assert result.name == "Rahul"
    assert result.phone == "9876543210"
    assert result.configuration == "2 BHK"


def test_extract_malformed_json_then_valid_retry():
    llm = _make_llm(["not valid json{{{", '{"name": "Rahul", "phone": null, "budget": null, '
                      '"property_type": null, "configuration": null, "preferred_location": null, '
                      '"purpose": null, "purchase_timeline": null, "requirements": null, '
                      '"intent_score": 0, "lead_status": "cold", "ready_for_visit": false}'])
    extractor = LeadExtractor(llm)

    result = extractor.extract([{"role": "user", "content": "hi"}], LeadData())

    assert result.name == "Rahul"
    assert llm.chat_json.call_count == 2


def test_extract_persistent_malformed_json_keeps_previous_lead():
    llm = _make_llm(["broken 1", "broken 2"])
    extractor = LeadExtractor(llm)
    previous = LeadData(name="Existing Name")

    result = extractor.extract([{"role": "user", "content": "hi"}], previous)

    assert result == previous
    assert llm.chat_json.call_count == 2


def test_extract_missing_required_keys_falls_back():
    llm = _make_llm(['{"unexpected": "shape"}', '{"still": "wrong"}'])
    extractor = LeadExtractor(llm)
    previous = LeadData(name="Existing Name")

    result = extractor.extract([{"role": "user", "content": "hi"}], previous)

    # Pydantic model has defaults for all fields, so this actually validates —
    # but the unrelated "name" field should not be silently dropped from previous state
    # once merged, since new.name is None and previous.name is kept.
    assert result.name == "Existing Name"


def test_extract_llm_unavailable_keeps_previous_lead():
    llm = MagicMock()
    llm.is_available = False
    extractor = LeadExtractor(llm)
    previous = LeadData(name="Existing Name")

    result = extractor.extract([{"role": "user", "content": "hi"}], previous)

    assert result == previous
    llm.chat_json.assert_not_called()


def test_extract_never_raises_on_llm_error():
    llm = MagicMock()
    llm.is_available = True
    llm.chat_json.side_effect = LLMUnavailableError("down")
    extractor = LeadExtractor(llm)
    previous = LeadData(name="Existing Name")

    result = extractor.extract([{"role": "user", "content": "hi"}], previous)

    assert result == previous
