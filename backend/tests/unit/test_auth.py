import pytest
from app.auth.security import hash_password, verify_password, create_access_token, decode_token


class TestPasswordHashing:
    """Tests du hachage de mots de passe."""

    def test_hash_password_returns_string(self):
        hashed = hash_password("monmotdepasse")
        assert isinstance(hashed, str)

    def test_hash_password_different_from_plain(self):
        plain = "monmotdepasse"
        hashed = hash_password(plain)
        assert hashed != plain

    def test_verify_password_correct(self):
        plain = "monmotdepasse"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_password_incorrect(self):
        hashed = hash_password("bonmotdepasse")
        assert verify_password("mauvais", hashed) is False

    def test_two_hashes_different(self):
        """bcrypt génère un salt différent à chaque fois."""
        h1 = hash_password("mêmemotdepasse")
        h2 = hash_password("mêmemotdepasse")
        assert h1 != h2


class TestJWT:
    """Tests des tokens JWT."""

    def test_create_token_returns_string(self):
        token = create_access_token({"sub": "user-uuid-123", "role": "admin"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self):
        payload = {"sub": "user-uuid-123", "role": "admin"}
        token = create_access_token(payload)
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user-uuid-123"
        assert decoded["role"] == "admin"

    def test_decode_invalid_token(self):
        result = decode_token("token.invalide.ici")
        assert result is None

    def test_decode_tampered_token(self):
        token = create_access_token({"sub": "user-uuid-123"})
        tampered = token + "tampered"
        result = decode_token(tampered)
        assert result is None

    def test_token_contains_expiry(self):
        token = create_access_token({"sub": "user-uuid-123"})
        decoded = decode_token(token)
        assert "exp" in decoded


class TestAuthEndpoints:
    """Tests des endpoints d'authentification."""

    def test_login_success(self, client, admin_user):
        response = client.post("/auth/login", json={
            "login": "test_admin",
            "password": "testpass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "admin"

    def test_login_wrong_password(self, client, admin_user):
        response = client.post("/auth/login", json={
            "login": "test_admin",
            "password": "mauvaismdp"
        })
        assert response.status_code == 401
        assert "Incorrect" in response.json()["detail"]

    def test_login_unknown_user(self, client):
        response = client.post("/auth/login", json={
            "login": "inexistant",
            "password": "password123"
        })
        assert response.status_code == 401

    def test_login_inactive_user(self, client, db, reference_data):
        from app.models.users import User
        from app.auth.security import hash_password
        user = User(
            login="inactif",
            password_hash=hash_password("pass123"),
            role_id=reference_data["role_admin"].id,
            is_active=False,
        )
        db.add(user)
        db.commit()

        response = client.post("/auth/login", json={
            "login": "inactif",
            "password": "pass123"
        })
        assert response.status_code == 401

    def test_get_me_authenticated(self, client, admin_headers):
        response = client.get("/auth/me", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["login"] == "test_admin"
        assert data["role"] == "admin"

    def test_get_me_no_token(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client):
        response = client.get("/auth/me", headers={
            "Authorization": "Bearer tokeninvalide"
        })
        assert response.status_code == 401