import pytest

from conftest import denied, ok, post


def test_simulations_are_private_and_trading_advancing_grant_no_xp(account):
    alice, _ = account()
    bob, bob_data = account()
    before_alice = ok(alice.get("/api/simulation"))
    before_bob = ok(bob.get("/api/simulation"))
    xp = ok(alice.get("/api/me/dashboard"))["xp"]
    ticker = before_alice["companies"][0]["ticker"]
    ok(post(alice, "/simulation/trade", {
        "side": "buy", "ticker": ticker, "qty": 1,
        "thesis": "A small position limits exposure while I study the company.",
    }))
    traded = ok(alice.get("/api/simulation"))
    assert traded["portfolio"]["cash"] < before_alice["portfolio"]["cash"]
    assert traded["portfolio"]["holdings"][ticker] == before_alice["portfolio"]["holdings"].get(ticker, 0) + 1
    ok(post(alice, "/simulation/advance"))
    assert ok(alice.get("/api/simulation"))["summary"]["sim_day"] == before_alice["summary"]["sim_day"] + 1
    assert ok(bob.get("/api/simulation")) == before_bob
    assert ok(alice.get("/api/me/dashboard"))["xp"] == xp
    # Supplying someone else's ID must not let a caller select their world.
    response = post(alice, "/simulation/advance", {"user_id": bob_data["user"]["id"]})
    assert response.status_code in (200, 400, 422), response.text
    assert ok(bob.get("/api/simulation")) == before_bob


@pytest.mark.parametrize("qty", [0, -1, 1.5, True, "NaN", "Infinity", 10**15])
def test_invalid_trade_quantity_is_rejected_without_mutation(account, qty):
    client, _ = account()
    before = ok(client.get("/api/simulation"))
    denied(post(client, "/simulation/trade", {
        "side": "buy", "ticker": before["companies"][0]["ticker"], "qty": qty,
        "thesis": "Testing invalid trade input must not modify the portfolio.",
    }), (400, 422))
    assert ok(client.get("/api/simulation")) == before


def test_quiz_is_scored_server_side_and_completion_reward_is_once(account):
    client, _ = account()
    lessons = ok(client.get("/api/lessons"))
    lesson = next(item for item in lessons if not item["premium"] and not item["locked"])
    assert not {"answer", "correct_answer", "answer_index", "correct_index"} & lesson.keys()
    start = ok(client.get("/api/me/rewards"))
    results = []
    for answer in range(len(lesson["options"])):
        response = ok(post(client, f"/lessons/{lesson['id']}/complete", {"answer": answer}))
        results.append((answer, response))
        if not response["correct"]:
            assert response["xp_awarded"] == 0
    correct = [(answer, result) for answer, result in results if result["correct"]]
    assert len(correct) == 1
    assert correct[0][1]["xp_awarded"] == lesson["xp"]
    after = ok(client.get("/api/me/rewards"))
    assert after["xp"] == start["xp"] + lesson["xp"]
    assert len(after["ledger"]) == len(start["ledger"]) + 1
    response = post(client, f"/lessons/{lesson['id']}/complete", {"answer": correct[0][0]})
    if response.is_success:
        assert ok(response)["xp_awarded"] == 0
    else:
        denied(response, (409,))
    assert ok(client.get("/api/me/rewards")) == after
    assert next(item for item in ok(client.get("/api/lessons")) if item["id"] == lesson["id"])["completed"] is True


def test_free_user_cannot_complete_premium_lesson(account):
    client, _ = account()
    premium = [item for item in ok(client.get("/api/lessons")) if item["premium"]]
    assert premium, "Premium guard needs at least one premium lesson"
    before = ok(client.get("/api/me/rewards"))
    for lesson in premium:
        assert lesson["locked"] is True
        denied(post(client, f"/lessons/{lesson['id']}/complete", {"answer": 0}), (403,))
    assert ok(client.get("/api/me/rewards")) == before


def test_reflection_requires_meaningful_text_and_real_day_cap(account):
    client, _ = account()
    before = ok(client.get("/api/me/rewards"))
    short = post(client, "/simulation/reflect", {"text": "ok"})
    if short.is_success:
        assert ok(short)["xp_awarded"] == 0
    else:
        denied(short, (400, 422))
    assert ok(client.get("/api/me/rewards"))["xp"] == before["xp"]
    text = "I compared the company's exposure to supply disruptions and market demand. Next time I will diversify rather than concentrate my entire portfolio in one sector."
    first = ok(post(client, "/simulation/reflect", {"text": text}))
    assert first["xp_awarded"] > 0
    after = ok(client.get("/api/me/rewards"))
    assert after["xp"] == before["xp"] + first["xp_awarded"]
    ok(post(client, "/simulation/advance"))
    second = post(client, "/simulation/reflect", {"text": text + " I will also maintain cash reserves."})
    if second.is_success:
        assert ok(second)["xp_awarded"] == 0
    else:
        denied(second, (400, 409, 429))
    assert ok(client.get("/api/me/rewards")) == after


def test_cosmetics_cannot_be_redeemed_without_credits(account):
    client, _ = account()
    before = ok(client.get("/api/me/rewards"))
    assert before["credits"] == 0
    reward = next(item for item in before["catalog"] if item["cost"] > 0 and not item["owned"])
    denied(post(client, "/me/rewards/redeem", {"reward_id": reward["id"]}), (400, 403, 409))
    assert ok(client.get("/api/me/rewards")) == before
