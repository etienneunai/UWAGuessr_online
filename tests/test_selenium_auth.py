import unittest
import threading
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from app import app, db
from app.models import User, Photos
from app.test_config import TestConfig


class AuthSeleniumTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config.from_object(TestConfig)

        cls.app_context = app.app_context()
        cls.app_context.push()

        db.drop_all()
        db.create_all()

        sample_photo = Photos(
            image_path="test.webp",
            latitude=-31.98,
            longitude=115.81
        )
        db.session.add(sample_photo)
        db.session.commit()

        cls.server_thread = threading.Thread(
            target=lambda: app.run(port=5051, use_reloader=False)
        )
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(2)

        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        cls.driver = webdriver.Chrome(options=options)
        cls.base_url = "http://127.0.0.1:5051"
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        db.session.remove()
        db.drop_all()
        cls.app_context.pop()

    def setUp(self):
        User.query.delete()
        db.session.commit()


    def _click(self, element):
        """Scroll element into view then click"""
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", element
        )
        time.sleep(0.2)
        element.click()

    def _wait_for_alert(self):
        return self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "#alertArea .alert"))
        )

    def _signup_via_ui(self, username="testuser", email="test@example.com",
                       password="Password1", question="Pet name?", answer="Fluffy"):
        self.driver.get(self.base_url + "/signup")

        self.wait.until(EC.visibility_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys(username)
        self.driver.find_element(By.ID, "email").send_keys(email)
        self._click(self.driver.find_element(By.ID, "nextBtn1"))

        self.wait.until(EC.visibility_of_element_located((By.ID, "password")))
        self.driver.find_element(By.ID, "password").send_keys(password)
        self.driver.find_element(By.ID, "confirmPassword").send_keys(password)
        self._click(self.driver.find_element(By.ID, "nextBtn2"))

        self.wait.until(EC.visibility_of_element_located((By.ID, "securityQuestion")))
        self.driver.find_element(By.ID, "securityQuestion").send_keys(question)
        self.driver.find_element(By.ID, "securityAnswer").send_keys(answer)
        self._click(self.driver.find_element(By.ID, "signupBtn"))

    def _login_via_ui(self, email="test@example.com", password="Password1"):
        self.driver.get(self.base_url + "/login")
        self.wait.until(EC.visibility_of_element_located((By.ID, "email")))
        self.driver.find_element(By.ID, "email").send_keys(email)
        self.driver.find_element(By.ID, "password").send_keys(password)
        self._click(self.driver.find_element(By.ID, "signinBtn"))

    # Signup

    def test_signup_success_redirects(self):
        self._signup_via_ui()
        self.wait.until(EC.url_changes(self.base_url + "/signup"))
        self.assertNotIn("/signup", self.driver.current_url,
            f"Expected redirect after signup but stayed at {self.driver.current_url}")

    def test_signup_step1_empty_username_shows_error(self):
        self.driver.get(self.base_url + "/signup")
        self.wait.until(EC.visibility_of_element_located((By.ID, "email")))
        self.driver.find_element(By.ID, "email").send_keys("test@example.com")
        self._click(self.driver.find_element(By.ID, "nextBtn1"))
        alert = self._wait_for_alert()
        self.assertIn("Username", alert.text,
            f"Expected username error but got: {alert.text}")

    def test_signup_step1_invalid_email_shows_error(self):
        self.driver.get(self.base_url + "/signup")
        self.wait.until(EC.visibility_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys("testuser")
        self.driver.find_element(By.ID, "email").send_keys("notanemail")
        self._click(self.driver.find_element(By.ID, "nextBtn1"))
        alert = self._wait_for_alert()
        self.assertIn("email", alert.text.lower(),
            f"Expected email error but got: {alert.text}")

    def test_signup_step2_password_mismatch_shows_error(self):
        self.driver.get(self.base_url + "/signup")
        self.wait.until(EC.visibility_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys("testuser")
        self.driver.find_element(By.ID, "email").send_keys("test@example.com")
        self._click(self.driver.find_element(By.ID, "nextBtn1"))

        self.wait.until(EC.visibility_of_element_located((By.ID, "password")))
        self.driver.find_element(By.ID, "password").send_keys("Password1")
        self.driver.find_element(By.ID, "confirmPassword").send_keys("Different1")
        self._click(self.driver.find_element(By.ID, "nextBtn2"))
        alert = self._wait_for_alert()
        self.assertIn("match", alert.text.lower(),
            f"Expected password mismatch error but got: {alert.text}")

    def test_signup_step2_weak_password_shows_error(self):
        self.driver.get(self.base_url + "/signup")
        self.wait.until(EC.visibility_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys("testuser")
        self.driver.find_element(By.ID, "email").send_keys("test@example.com")
        self._click(self.driver.find_element(By.ID, "nextBtn1"))

        self.wait.until(EC.visibility_of_element_located((By.ID, "password")))
        self.driver.find_element(By.ID, "password").send_keys("weak")
        self.driver.find_element(By.ID, "confirmPassword").send_keys("weak")
        self._click(self.driver.find_element(By.ID, "nextBtn2"))
        alert = self._wait_for_alert()
        self.assertIn("password", alert.text.lower(),
            f"Expected password error but got: {alert.text}")

    def test_signup_back_button_returns_to_step1(self):
        self.driver.get(self.base_url + "/signup")
        self.wait.until(EC.visibility_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys("testuser")
        self.driver.find_element(By.ID, "email").send_keys("test@example.com")
        self._click(self.driver.find_element(By.ID, "nextBtn1"))

        self.wait.until(EC.visibility_of_element_located((By.ID, "backBtn2")))
        self._click(self.driver.find_element(By.ID, "backBtn2"))
        self.wait.until(EC.visibility_of_element_located((By.ID, "username")))
        self.assertTrue(
            self.driver.find_element(By.ID, "step-1").is_displayed(),
            "Expected step 1 to be visible after clicking back"
        )

    # Login

    def test_login_success_redirects(self):
        self._signup_via_ui()
        self.wait.until(EC.url_changes(self.base_url + "/signup"))
        self._login_via_ui()
        self.wait.until(EC.url_changes(self.base_url + "/login"))
        self.assertNotIn("/login", self.driver.current_url,
            f"Expected redirect after login but stayed at {self.driver.current_url}")

    def test_login_wrong_password_shows_error(self):
        self._signup_via_ui()
        self.wait.until(EC.url_changes(self.base_url + "/signup"))
        self._login_via_ui(password="WrongPassword1")
        alert = self._wait_for_alert()
        self.assertIn("incorrect", alert.text.lower(),
            f"Expected incorrect credentials error but got: {alert.text}")

    def test_login_nonexistent_email_shows_error(self):
        self._login_via_ui(email="ghost@example.com")
        alert = self._wait_for_alert()
        self.assertIn("incorrect", alert.text.lower(),
            f"Expected incorrect credentials error but got: {alert.text}")

    def test_login_empty_fields_shows_error(self):
        self.driver.get(self.base_url + "/login")
        self.wait.until(EC.visibility_of_element_located((By.ID, "signinBtn")))
        self._click(self.driver.find_element(By.ID, "signinBtn"))
        alert = self._wait_for_alert()
        self.assertTrue(alert.is_displayed(),
            "Expected an error alert for empty login form")

    # Forgot Password

    def test_forgot_password_unknown_email_shows_error(self):
        self.driver.get(self.base_url + "/forgot-password")
        self.wait.until(EC.visibility_of_element_located((By.ID, "email")))
        self.driver.find_element(By.ID, "email").send_keys("ghost@example.com")
        self._click(self.driver.find_element(By.ID, "fpNextBtn"))
        alert = self._wait_for_alert()
        self.assertIn("found", alert.text.lower(),
            f"Expected not found error but got: {alert.text}")

    def test_forgot_password_shows_security_question(self):
        self._signup_via_ui(question="Pet name?")
        self.wait.until(EC.url_changes(self.base_url + "/signup"))

        self.driver.get(self.base_url + "/forgot-password")
        self.wait.until(EC.visibility_of_element_located((By.ID, "email")))
        self.driver.find_element(By.ID, "email").send_keys("test@example.com")
        self._click(self.driver.find_element(By.ID, "fpNextBtn"))

        self.wait.until(EC.visibility_of_element_located((By.ID, "fp-step-2")))
        question_text = self.driver.find_element(By.ID, "securityQuestionText").text
        self.assertEqual(question_text, "Pet name?",
            f"Expected security question to be displayed but got: '{question_text}'")

    def test_forgot_password_wrong_answer_shows_error(self):
        self._signup_via_ui(answer="Fluffy")
        self.wait.until(EC.url_changes(self.base_url + "/signup"))

        self.driver.get(self.base_url + "/forgot-password")
        self.wait.until(EC.visibility_of_element_located((By.ID, "email")))
        self.driver.find_element(By.ID, "email").send_keys("test@example.com")
        self._click(self.driver.find_element(By.ID, "fpNextBtn"))

        self.wait.until(EC.visibility_of_element_located((By.ID, "fp-step-2")))
        self.driver.find_element(By.ID, "securityAnswer").send_keys("WrongAnswer")
        self.driver.find_element(By.ID, "newPassword").send_keys("NewPassword1")
        self.driver.find_element(By.ID, "confirmPassword").send_keys("NewPassword1")
        self._click(self.driver.find_element(By.ID, "resetBtn"))
        alert = self._wait_for_alert()
        self.assertTrue(alert.is_displayed(),
            f"Expected error alert for wrong answer but got: {alert.text}")

    def test_forgot_password_success_redirects(self):
        self._signup_via_ui(answer="Fluffy")
        self.wait.until(EC.url_changes(self.base_url + "/signup"))

        self.driver.get(self.base_url + "/forgot-password")
        self.wait.until(EC.visibility_of_element_located((By.ID, "email")))
        self.driver.find_element(By.ID, "email").send_keys("test@example.com")
        self._click(self.driver.find_element(By.ID, "fpNextBtn"))

        self.wait.until(EC.visibility_of_element_located((By.ID, "fp-step-2")))
        self.driver.find_element(By.ID, "securityAnswer").send_keys("Fluffy")
        self.driver.find_element(By.ID, "newPassword").send_keys("NewPassword1")
        self.driver.find_element(By.ID, "confirmPassword").send_keys("NewPassword1")
        self._click(self.driver.find_element(By.ID, "resetBtn"))

        self.wait.until(EC.url_contains("/login"))
        self.assertIn("/login", self.driver.current_url,
            f"Expected redirect to /login after reset but got: {self.driver.current_url}")

    def test_forgot_password_back_button_returns_to_step1(self):
        self._signup_via_ui()
        self.wait.until(EC.url_changes(self.base_url + "/signup"))

        self.driver.get(self.base_url + "/forgot-password")
        self.wait.until(EC.visibility_of_element_located((By.ID, "email")))
        self.driver.find_element(By.ID, "email").send_keys("test@example.com")
        self._click(self.driver.find_element(By.ID, "fpNextBtn"))

        self.wait.until(EC.visibility_of_element_located((By.ID, "fpBackBtn")))
        self._click(self.driver.find_element(By.ID, "fpBackBtn"))
        self.wait.until(EC.visibility_of_element_located((By.ID, "fp-step-1")))
        self.assertTrue(
            self.driver.find_element(By.ID, "fp-step-1").is_displayed(),
            "Expected step 1 to be visible after clicking back"
        )


if __name__ == "__main__":
    unittest.main()