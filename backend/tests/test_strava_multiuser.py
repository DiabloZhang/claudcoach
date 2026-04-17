import pytest

from db.models import User, Activity
from auth.security import get_password_hash, create_access_token
from strava.sync import parse_activity


class TestParseActivity:
    def test_parse_assigns_user_id(self):
        raw = {
            "id": 123456789,
            "name": "Morning Run",
            "sport_type": "Run",
            "start_date": "2026-04-01T07:00:00Z",
            "start_date_local": "2026-04-01T15:00:00Z",
            "timezone": "(GMT+08:00) Asia/Shanghai",
            "distance": 10000,
            "moving_time": 3600,
            "elapsed_time": 3700,
            "total_elevation_gain": 50,
            "average_speed": 2.78,
        }
        act = parse_activity(raw, user_id=42)
        assert act.user_id == 42
        assert act.strava_id == 123456789
        assert act.name == "Morning Run"


class TestActivityStravaIdConstraint:
    """验证同一 strava_id 可以在不同用户下共存，但同一用户下不能重复"""

    def test_same_strava_id_for_different_users(self, db_session):
        user_a = User(email="a@test.com", password_hash=get_password_hash("pass"))
        user_b = User(email="b@test.com", password_hash=get_password_hash("pass"))
        db_session.add_all([user_a, user_b])
        db_session.commit()

        act_a = Activity(user_id=user_a.id, strava_id=999, name="Run A")
        act_b = Activity(user_id=user_b.id, strava_id=999, name="Run B")
        db_session.add_all([act_a, act_b])
        db_session.commit()

        assert db_session.query(Activity).filter_by(user_id=user_a.id).count() == 1
        assert db_session.query(Activity).filter_by(user_id=user_b.id).count() == 1

    def test_duplicate_strava_id_same_user_blocked(self, db_session):
        user = User(email="c@test.com", password_hash=get_password_hash("pass"))
        db_session.add(user)
        db_session.commit()

        act1 = Activity(user_id=user.id, strava_id=888, name="First")
        db_session.add(act1)
        db_session.commit()

        act2 = Activity(user_id=user.id, strava_id=888, name="Second")
        db_session.add(act2)
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestSyncExistsIsolation:
    """模拟 sync_user_activities 中的 exists 检查，验证它按 user_id 过滤"""

    def test_exists_check_is_per_user(self, db_session):
        user_a = User(email="sync_a@test.com", password_hash=get_password_hash("pass"))
        user_b = User(email="sync_b@test.com", password_hash=get_password_hash("pass"))
        db_session.add_all([user_a, user_b])
        db_session.commit()

        # 用户 A 已同步该活动
        act = Activity(user_id=user_a.id, strava_id=777, name="Shared Event")
        db_session.add(act)
        db_session.commit()

        # 模拟 sync.py 中的 exists 查询（修复前只按 strava_id 查，会错误跳过）
        exists_for_a = db_session.query(Activity).filter(
            Activity.user_id == user_a.id,
            Activity.strava_id == 777,
        ).first()
        assert exists_for_a is not None

        exists_for_b = db_session.query(Activity).filter(
            Activity.user_id == user_b.id,
            Activity.strava_id == 777,
        ).first()
        assert exists_for_b is None


class TestStravaRouterAuth:
    def test_status_optional_auth(self, client):
        res = client.get("/strava/status")
        assert res.status_code == 200
        assert res.json()["authenticated"] is False

    def test_status_returns_user_info(self, client, db_session):
        user = User(email="status@test.com", password_hash=get_password_hash("pass"), nickname="Runner")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token = create_access_token({"sub": str(user.id)})
        res = client.get("/strava/status", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["authenticated"] is True
        assert res.json()["nickname"] == "Runner"
