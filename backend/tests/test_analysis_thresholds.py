from db.models import User
from auth.security import get_password_hash, create_access_token


class TestThresholdsUpdate:
    def test_update_thresholds_via_json_body(self, client, db_session):
        user = User(
            email="thresholds@example.com",
            password_hash=get_password_hash("pass"),
            ftp=200.0,
            lthr=150.0,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token = create_access_token({"sub": str(user.id)})
        res = client.put(
            "/analysis/thresholds",
            json={"ftp": 250.0, "lthr": 160.0, "css": 95.0, "run_threshold_pace": 240.0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["message"] == "阈值已更新"
        assert data["ftp"] == 250.0
        assert data["lthr"] == 160.0
        assert data["css"] == 95.0
        assert data["run_threshold_pace"] == 240.0

    def test_update_thresholds_partial(self, client, db_session):
        user = User(
            email="partial@example.com",
            password_hash=get_password_hash("pass"),
            ftp=200.0,
            lthr=150.0,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token = create_access_token({"sub": str(user.id)})
        res = client.put(
            "/analysis/thresholds",
            json={"ftp": 280.0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["ftp"] == 280.0
        assert data["lthr"] == 150.0  # unchanged
        assert data["css"] is None
        assert data["run_threshold_pace"] is None

    def test_update_thresholds_unauthorized(self, client):
        res = client.put("/analysis/thresholds", json={"ftp": 250.0})
        assert res.status_code == 401
