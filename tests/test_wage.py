from core.services.wage_service import get_hour_rates

def test_get_hour_rates_smoke(session):
    # session: pytest-fixture, initialisiert eine in-memory DB + Profile
    gh, nh = get_hour_rates(session, user_id=1)
    assert gh >= 0 and nh >= 0
