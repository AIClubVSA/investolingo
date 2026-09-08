import pytest

from conftest import denied, ok, post


@pytest.fixture
def classroom(educator, account):
    teacher, _ = educator()
    student, data = account()
    room = ok(post(teacher, "/classes", {"name": "Integration Economics"}))
    ok(post(student, "/classes/join", {"code": room["code"]}))
    return teacher, student, data["user"]["id"], room


def test_classroom_membership_assignment_and_owner_scope(classroom, educator, account):
    teacher, student, student_id, room = classroom
    rival, _ = educator()
    outsider, outsider_data = account()
    class_path = f"/classes/{room['id']}"
    assert [item["id"] for item in ok(teacher.get("/api/classes"))] == [room["id"]]
    assert [item["id"] for item in ok(student.get("/api/classes"))] == [room["id"]]
    assert ok(rival.get("/api/classes")) == []
    assert ok(outsider.get("/api/classes")) == []
    detail = ok(teacher.get("/api" + class_path))
    assert [item["id"] for item in detail["students"]] == [student_id]
    for item in detail["students"]:
        assert not {"email", "password_hash", "birth_date"} & item.keys()
    lesson = next(item for item in ok(teacher.get("/api/lessons")) if not item["premium"])
    assignment = {"lesson_id": lesson["id"], "title": "Understand risk"}
    award = {"student_id": student_id, "amount": 10, "reason": "Good analysis", "idempotency_key": "unauthorized-award"}
    for caller in (rival, student, outsider):
        denied(caller.get("/api" + class_path), (403, 404))
        denied(post(caller, class_path + "/assignments", assignment), (403, 404))
        denied(post(caller, class_path + "/rewards", award), (403, 404))
        denied(post(caller, class_path + "/remove", {"student_id": student_id}), (403, 404))
    denied(post(student, "/classes", {"name": "Student-created"}), (403,))
    denied(post(teacher, class_path + "/rewards", {**award, "student_id": outsider_data["user"]["id"]}), (400, 403, 404))
    assert ok(student.get("/api/me/dashboard"))["xp"] == 0
    ok(post(teacher, class_path + "/assignments", assignment))
    detail = ok(teacher.get("/api" + class_path))
    assert len(detail["assignments"]) == 1
    assert detail["assignments"][0]["lesson_id"] == lesson["id"]
    ok(post(teacher, class_path + "/remove", {"student_id": student_id}))
    assert ok(student.get("/api/classes")) == []
    denied(post(teacher, class_path + "/rewards", award), (400, 403, 404))


def test_join_is_idempotent_and_invalid_codes_are_rejected(classroom):
    teacher, student, _, room = classroom
    response = post(student, "/classes/join", {"code": room["code"]})
    if response.is_success:
        assert ok(response)["ok"] is True
    else:
        denied(response, (409,))
    assert ok(teacher.get("/api/classes"))[0]["member_count"] == 1
    denied(post(student, "/classes/join", {"code": "NOTREAL"}), (400, 404, 422))


def test_educator_awards_idempotent_and_capped_across_classes_and_educators(classroom, educator):
    teacher, student, student_id, room = classroom
    endpoint = f"/classes/{room['id']}/rewards"
    payload = {"student_id": student_id, "amount": 60, "reason": "Thoughtful analysis", "idempotency_key": "award-one"}
    before = ok(student.get("/api/me/rewards"))
    ok(post(teacher, endpoint, payload))
    once = ok(student.get("/api/me/rewards"))
    assert once["xp"] == before["xp"] + 60
    assert len(once["ledger"]) == len(before["ledger"]) + 1
    ok(post(teacher, endpoint, payload))
    assert ok(student.get("/api/me/rewards")) == once
    # Reusing a key with another amount must not become a second credit.
    replay = post(teacher, endpoint, {**payload, "amount": 40})
    if not replay.is_success:
        denied(replay, (400, 409))
    assert ok(student.get("/api/me/rewards")) == once
    denied(post(teacher, endpoint, {**payload, "amount": 41, "idempotency_key": "over-cap"}), (400, 403, 409, 429))
    assert ok(student.get("/api/me/rewards")) == once
    second_teacher, _ = educator()
    other_room = ok(post(second_teacher, "/classes", {"name": "Another economics class"}))
    ok(post(student, "/classes/join", {"code": other_room["code"]}))
    other_endpoint = f"/classes/{other_room['id']}/rewards"
    ok(post(second_teacher, other_endpoint, {**payload, "amount": 40, "idempotency_key": "award-two"}))
    capped = ok(student.get("/api/me/rewards"))
    assert capped["xp"] == before["xp"] + 100
    for caller, path in ((teacher, endpoint), (second_teacher, other_endpoint)):
        denied(post(caller, path, {**payload, "amount": 1, "idempotency_key": "one-too-many"}), (400, 403, 409, 429))
    # An exact retry still succeeds even when the daily cap has been reached.
    ok(post(teacher, endpoint, payload))
    assert ok(student.get("/api/me/rewards")) == capped


@pytest.mark.parametrize("amount", [0, -1, 101, 1.5, True])
def test_invalid_educator_awards_leave_ledger_unchanged(classroom, amount):
    teacher, student, student_id, room = classroom
    before = ok(student.get("/api/me/rewards"))
    denied(post(teacher, f"/classes/{room['id']}/rewards", {
        "student_id": student_id, "amount": amount,
        "reason": "Invalid amount test", "idempotency_key": "invalid-award",
    }), (400, 422))
    assert ok(student.get("/api/me/rewards")) == before


def test_redemption_spends_credits_not_lifetime_xp_and_cannot_repeat(classroom):
    teacher, student, student_id, room = classroom
    ok(post(teacher, f"/classes/{room['id']}/rewards", {
        "student_id": student_id, "amount": 100,
        "reason": "Excellent analysis", "idempotency_key": "cosmetic-funding",
    }))
    before = ok(student.get("/api/me/rewards"))
    reward = next(item for item in before["catalog"] if 0 < item["cost"] <= before["credits"])
    payload = {"reward_id": reward["id"]}
    ok(post(student, "/me/rewards/redeem", payload))
    after = ok(student.get("/api/me/rewards"))
    assert after["xp"] == before["xp"]
    assert after["level"] == before["level"]
    assert after["credits"] == before["credits"] - reward["cost"]
    assert next(item for item in after["catalog"] if item["id"] == reward["id"])["owned"] is True
    replay = post(student, "/me/rewards/redeem", payload)
    if not replay.is_success:
        denied(replay, (400, 409))
    assert ok(student.get("/api/me/rewards")) == after
