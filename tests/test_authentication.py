import unittest
from app import app, db
from app.models import User
from app.test_config import TestConfig


class AuthTests(unittest.TestCase):

    def setUp(self):
        app.config.from_object(TestConfig)
        self.app_context = app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _signup(self, username="testuser", email="test@example.com",
                password="Password1", question="Pet name?", answer="Fluffy"):
        return self.client.post("/api/signup", json={
            "username": username,
            "email": email,
            "password": password,
            "securityQuestion": question,
            "securityAnswer": answer,
        })

    def _login(self, email="test@example.com", password="Password1"):
        return self.client.post("/api/login", json={
            "email": email,
            "password": password,
        })

    def _get_security_question(self, email="test@example.com"):
        return self.client.post("/api/get-security-question", json={
            "email": email,
        })

    def _reset_password(self, email="test@example.com",
                        answer="Fluffy", new_password="NewPassword1"):
        return self.client.post("/api/forgot-password", json={
            "email": email,
            "securityAnswer": answer,
            "newPassword": new_password,
        })

    def assertResponse(self, response, expected_status):
        self.assertEqual(
            response.status_code, expected_status,
            f"Expected {expected_status}, got {response.status_code}. "
            f"Body: {response.get_json()}"
        )

    # Signup

    def test_signup_success(self):
        response = self._signup()
        self.assertResponse(response, 201)
        data = response.get_json()
        self.assertIn("redirect", data,
            f"Expected 'redirect' in response but got: {data}")

    def test_signup_creates_user_in_db(self):
        self._signup(email="newuser@example.com", username="newuser")
        user = User.query.filter_by(email="newuser@example.com").first()
        self.assertIsNotNone(user, "User should exist in DB after signup")
        self.assertEqual(user.username, "newuser")

    def test_signup_missing_username(self):
        response = self._signup(username="")
        self.assertResponse(response, 400)
        data = response.get_json()
        self.assertIn("username", data.get("errors", {}),
            f"Expected username error but got: {data}")

    def test_signup_username_too_short(self):
        response = self._signup(username="ab")
        self.assertResponse(response, 400)
        data = response.get_json()
        self.assertIn("username", data.get("errors", {}),
            f"Expected username error but got: {data}")

    def test_signup_invalid_username_characters(self):
        response = self._signup(username="bad user!")
        self.assertResponse(response, 400)
        data = response.get_json()
        self.assertIn("username", data.get("errors", {}),
            f"Expected username error but got: {data}")

    def test_signup_missing_email(self):
        response = self._signup(email="")
        self.assertResponse(response, 400)
        data = response.get_json()
        self.assertIn("email", data.get("errors", {}),
            f"Expected email error but got: {data}")

    def test_signup_invalid_email(self):
        response = self._signup(email="notanemail")
        self.assertResponse(response, 400)
        data = response.get_json()
        self.assertIn("email", data.get("errors", {}),
            f"Expected email error but got: {data}")

    def test_signup_duplicate_email(self):
        self._signup(email="dupe@example.com", username="user1")
        response = self._signup(email="dupe@example.com", username="user2")
        self.assertResponse(response, 400)

    def test_signup_duplicate_username(self):
        self._signup(username="sameuser", email="user1@example.com")
        response = self._signup(username="sameuser", email="user2@example.com")
        self.assertResponse(response, 400)

    def test_signup_password_too_short(self):
        response = self._signup(password="Abc1")
        self.assertResponse(response, 400)
        data = response.get_json()
        self.assertIn("password", data.get("errors", {}),
            f"Expected password error but got: {data}")

    def test_signup_password_no_uppercase(self):
        response = self._signup(password="password1")
        self.assertResponse(response, 400)
        data = response.get_json()
        self.assertIn("password", data.get("errors", {}),
            f"Expected password error but got: {data}")

    def test_signup_password_no_number(self):
        response = self._signup(password="PasswordOnly")
        self.assertResponse(response, 400)
        data = response.get_json()
        self.assertIn("password", data.get("errors", {}),
            f"Expected password error but got: {data}")

    def test_signup_missing_security_question(self):
        response = self._signup(question="")
        self.assertResponse(response, 400)
        data = response.get_json()
        self.assertIn("securityQuestion", data.get("errors", {}),
            f"Expected securityQuestion error but got: {data}")

    def test_signup_missing_security_answer(self):
        response = self._signup(answer="")
        self.assertResponse(response, 400)
        data = response.get_json()
        self.assertIn("securityAnswer", data.get("errors", {}),
            f"Expected securityAnswer error but got: {data}")

    # Login

    def test_login_success(self):
        self._signup()
        response = self._login()
        self.assertResponse(response, 200)
        data = response.get_json()
        self.assertIn("redirect", data,
            f"Expected 'redirect' in response but got: {data}")

    def test_login_wrong_password(self):
        self._signup()
        response = self._login(password="WrongPassword1")
        self.assertResponse(response, 401)

    def test_login_nonexistent_email(self):
        response = self._login(email="ghost@example.com")
        self.assertResponse(response, 401)

    def test_login_missing_email(self):
        response = self._login(email="")
        self.assertResponse(response, 401)

    def test_login_invalid_email_format(self):
        response = self._login(email="notanemail")
        self.assertResponse(response, 401)

    def test_login_missing_password(self):
        response = self._login(password="")
        self.assertResponse(response, 401)

    def test_login_sets_session(self):
        self._signup()
        with self.client as c:
            c.post("/api/login", json={
                "email": "test@example.com",
                "password": "Password1",
            })
            with c.session_transaction() as sess:
                self.assertIn("_user_id", sess,
                    "Session should contain _user_id after login")

    # Forgot Password

    def test_get_security_question_success(self):
        self._signup(question="Pet name?")
        response = self._get_security_question()
        self.assertResponse(response, 200)
        data = response.get_json()
        self.assertIn("securityQuestion", data,
            f"Expected 'securityQuestion' in response but got: {data}")
        self.assertEqual(data["securityQuestion"], "Pet name?",
            f"Security question mismatch: {data}")

    def test_get_security_question_unknown_email(self):
        response = self._get_security_question(email="ghost@example.com")
        self.assertResponse(response, 404)

    def test_reset_password_success(self):
        self._signup(answer="Fluffy")
        response = self._reset_password(answer="Fluffy", new_password="NewPassword1")
        self.assertResponse(response, 200)

    def test_reset_password_actually_changes_password(self):
        self._signup(answer="Fluffy")
        self._reset_password(answer="Fluffy", new_password="NewPassword1")
        # Old password should no longer work
        old_login = self._login(password="Password1")
        self.assertResponse(old_login, 401)
        # New password should work
        new_login = self._login(password="NewPassword1")
        self.assertResponse(new_login, 200)

    def test_reset_password_wrong_answer(self):
        self._signup(answer="Fluffy")
        response = self._reset_password(answer="WrongAnswer")
        self.assertResponse(response, 401)

    def test_reset_password_unknown_email(self):
        response = self._reset_password(email="ghost@example.com")
        self.assertResponse(response, 401)

    def test_reset_password_too_short(self):
        self._signup(answer="Fluffy")
        response = self._reset_password(answer="Fluffy", new_password="Abc1")
        self.assertResponse(response, 401)

    def test_reset_password_no_uppercase(self):
        self._signup(answer="Fluffy")
        response = self._reset_password(answer="Fluffy", new_password="newpassword1")
        self.assertResponse(response, 401)

    def test_reset_password_no_number(self):
        self._signup(answer="Fluffy")
        response = self._reset_password(answer="Fluffy", new_password="NewPassword")
        self.assertResponse(response, 401)

    def test_reset_password_case_insensitive_answer(self):
        self._signup(answer="Fluffy")
        response = self._reset_password(answer="fluffy", new_password="NewPassword1")
        self.assertResponse(response, 200)


if __name__ == "__main__":
    unittest.main()