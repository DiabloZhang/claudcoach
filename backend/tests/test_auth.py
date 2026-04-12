from db.models import User
from auth.security import verify_password, get_password_hash, create_access_token, decode_access_token


class TestSecurity:
    def test_password_hash_and_verify(self):
        hashed = get_password_hash("secret123")
        assert verify_password("secret123", hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_create_and_decode_token(self):
        token = create_access_token({"sub": "42"})
        payload = decode_access_token(token)
        assert payload["sub"] == "42"
        assert "exp" in payload

    def test_decode_invalid_token(self):
        assert decode_access_token("not.a.token") is None


class TestAuthRouter:
    def test_register_and_login(self, client):
        # 注册
        res = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "secret123",
            "nickname": "Tester",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["access_token"]
        assert data["user"]["email"] == "test@example.com"

        # 登录
        res = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "secret123",
        })
        assert res.status_code == 200
        assert res.json()["user"]["nickname"] == "Tester"

    def test_login_wrong_password(self, client):
        client.post("/auth/register", json={
            "email": "test2@example.com",
            "password": "secret123",
        })
        res = client.post("/auth/login", json={
            "email": "test2@example.com",
            "password": "wrong",
        })
        assert res.status_code == 400

    def test_me_requires_auth(self, client):
        res = client.get("/auth/me")
        assert res.status_code == 401

    def test_me_with_token(self, client, db_session):
        user = User(email="me@example.com", password_hash=get_password_hash("pass"), nickname="Me")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token = create_access_token({"sub": str(user.id)})
        res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["email"] == "me@example.com"

    def test_update_profile(self, client, db_session):
        user = User(email="profile@example.com", password_hash=get_password_hash("pass"))
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token = create_access_token({"sub": str(user.id)})
        res = client.put("/auth/profile", json={"nickname": "NewName", "timezone": "Asia/Tokyo"}, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["user"]["nickname"] == "NewName"
        assert res.json()["user"]["timezone"] == "Asia/Tokyo"

    def test_change_password(self, client, db_session):
        user = User(email="pwd@example.com", password_hash=get_password_hash("oldpass"))
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token = create_access_token({"sub": str(user.id)})
        res = client.post("/auth/change-password", json={"old_password": "oldpass", "new_password": "newpass"}, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200

        # 用新密码登录
        res = client.post("/auth/login", json={"email": "pwd@example.com", "password": "newpass"})
        assert res.status_code == 200

    def test_set_password_for_strava_only_user(self, client, db_session):
        """Strava-only 用户可以直接设置初始密码"""
        user = User(email="strava_only_pwd@example.com", password_hash=None, auth_provider="strava")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token = create_access_token({"sub": str(user.id)})
        res = client.post("/auth/change-password", json={"new_password": "firstpass"}, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200

        # 设置后可用新密码登录
        res = client.post("/auth/login", json={"email": "strava_only_pwd@example.com", "password": "firstpass"})
        assert res.status_code == 200

    def test_strava_disconnect_without_password_fails(self, client, db_session):
        """未设置密码的用户不应被允许解绑 Strava，避免账户被锁"""
        user = User(email="strava_only@example.com", password_hash=None, strava_athlete_id=12345, auth_provider="strava")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token = create_access_token({"sub": str(user.id)})
        res = client.post("/auth/strava/disconnect", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 400
        assert "密码" in res.json()["detail"]

    def test_strava_disconnect_with_password_succeeds(self, client, db_session):
        user = User(email="both@example.com", password_hash=get_password_hash("pass"), strava_athlete_id=12345, auth_provider="both")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token = create_access_token({"sub": str(user.id)})
        res = client.post("/auth/strava/disconnect", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        db_session.refresh(user)
        assert user.strava_athlete_id is None
        assert user.auth_provider == "password"


class TestDataIsolation:
    def test_user_cannot_access_another_users_data(self, client, db_session):
        from db.models import Activity

        user_a = User(email="a@example.com", password_hash=get_password_hash("pass"))
        user_b = User(email="b@example.com", password_hash=get_password_hash("pass"))
        db_session.add_all([user_a, user_b])
        db_session.commit()
        db_session.refresh(user_a)
        db_session.refresh(user_b)

        act = Activity(user_id=user_a.id, strava_id=1001, name="A's run")
        db_session.add(act)
        db_session.commit()

        token_b = create_access_token({"sub": str(user_b.id)})
        res = client.get("/strava/activities", headers={"Authorization": f"Bearer {token_b}"})
        assert res.status_code == 200
        assert res.json() == []

        token_a = create_access_token({"sub": str(user_a.id)})
        res = client.get("/strava/activities", headers={"Authorization": f"Bearer {token_a}"})
        assert res.status_code == 200
        assert len(res.json()) == 1
