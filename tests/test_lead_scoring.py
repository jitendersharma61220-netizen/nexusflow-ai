from agents.lead_extractor import LeadData
from scoring.lead_scoring import is_valid_phone, score_lead


def _lead(**kwargs) -> LeadData:
    return LeadData(**kwargs)


def test_empty_lead_is_cold():
    score, status = score_lead(_lead())
    assert status == "cold"
    assert score == 0


def test_hot_lead_boundary_at_80():
    lead = _lead(
        budget="1.5 Cr",  # +20
        configuration="2 BHK",  # +15
        purchase_timeline="immediate",  # +15
        phone="9876543210",  # +15
        requirements="asking about price and inventory",  # +15
        ready_for_visit=True,  # +10
    )
    score, status = score_lead(lead)
    assert score >= 80
    assert status == "hot"


def test_warm_lead_boundary_range():
    lead = _lead(
        budget="1.5 Cr",  # +20
        configuration="2 BHK",  # +15
        requirements="asking about price",  # +15
        purchase_timeline="later",  # +0
    )
    score, status = score_lead(lead)
    assert 50 <= score < 80
    assert status == "warm"


def test_cold_lead_below_50():
    lead = _lead(requirements="just browsing")
    score, status = score_lead(lead)
    assert score < 50
    assert status == "cold"


def test_score_clamped_to_100():
    lead = _lead(
        budget="2 Cr",
        configuration="3 BHK",
        purchase_timeline="immediate, ready to buy",
        phone="9876543210",
        requirements="price inventory availability possession brochure emi",
        ready_for_visit=True,
        preferred_location="Golf Course Road",
    )
    score, status = score_lead(lead, project_location="Golf Course Road, Gurgaon")
    assert score <= 100
    assert status == "hot"


def test_valid_phone_numbers():
    assert is_valid_phone("9876543210")
    assert is_valid_phone("+919876543210")
    assert is_valid_phone("987-654-3210")


def test_invalid_phone_numbers():
    assert not is_valid_phone(None)
    assert not is_valid_phone("")
    assert not is_valid_phone("12345")
    assert not is_valid_phone("abcdefghij")


def test_invalid_phone_excluded_from_score():
    lead_valid = _lead(phone="9876543210")
    lead_invalid = _lead(phone="12345")
    score_valid, _ = score_lead(lead_valid)
    score_invalid, _ = score_lead(lead_invalid)
    assert score_valid > score_invalid
