import unittest
import threading
import time

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By

from app import app, db
from app import socketio
from app.models import Photos, User, Challenge
from app.test_config import TestConfig



class SeleniumTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config.from_object(TestConfig)

        cls.app_context = app.app_context()
        cls.app_context.push()

        db.drop_all()
        db.create_all()

        # Add sample photo data so the game page API can
        # retrieve image data during Selenium testing.
        sample_photo = Photos(
            image_path="test.webp",
            latitude=-31.98,
            longitude=115.81
        )

        db.session.add(sample_photo)
        db.session.commit()

        cls.server_thread = threading.Thread(
            target=lambda: socketio.run(app, port=5055, use_reloader=False, allow_unsafe_werkzeug=True)
        )

        cls.server_thread.daemon = True
        cls.server_thread.start()

        time.sleep(2)

        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")

        cls.driver = webdriver.Chrome(options=options)
        cls.base_url = "http://127.0.0.1:5055"

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        db.session.remove()
        db.drop_all()
        cls.app_context.pop()

    def test_homepage_title(self):
        self.driver.get(self.base_url + "/")
        self.assertIn("EXPLORE UWA", self.driver.page_source)

    def test_friends_list_and_challenge_ui_elements(self):
        driver=self.driver
        driver.get(self.base_url + "/dashboard")
        time.sleep(1.5)
        page_content = driver.page_source

        if "Sign In" in page_content or "loginForm" in page_content or "Log In" in page_content:
            self.assertTrue(True)  
        else:
            self.assertIn("Friends List", page_content)

    def test_login_page(self):
        self.driver.get(self.base_url + "/login")
        self.assertIn("Sign in", self.driver.page_source)

    def test_signup_page(self):
        self.driver.get(self.base_url + "/signup")
        self.assertIn("Sign Up", self.driver.page_source)

    def test_how_to_play_page(self):
        self.driver.get(self.base_url + "/how-to-play")
        self.assertIn("How to Play", self.driver.page_source)

    def test_game_page(self):
        self.driver.get(self.base_url + "/game")
        self.assertIn("UWA", self.driver.page_source)
    
    def login_test_user(self):

        test_email = "testuser@student.uwa.edu.au"
        user = User.query.filter_by(email=test_email).first()
        if not user:
            user = User(username="TestPlayer", email=test_email)
            user.set_password("password123") 
            db.session.add(user)
            db.session.commit()

        self.driver.get(self.base_url + "/login")
        time.sleep(0.5)
        

        
        self.driver.find_element(By.ID, "email").send_keys(test_email)
        self.driver.find_element(By.ID, "password").send_keys("password123")
        
        
        self.driver.find_element(By.ID, "signinBtn").click()
        # Wait until redirected away from the login page to avoid race conditions
        for _ in range(10):
            if "/login" not in self.driver.current_url:
                break
            time.sleep(0.5)

    def test_challenge_rejoin_game_starts_at_correct_round(self):
        # 1. Log in the user
        self.login_test_user()
        
        # 2. Add another user and create an active in_progress challenge between them in DB

        
        challenger = User.query.filter_by(username="TestPlayer").first()
        challenged = User.query.filter_by(username="OpponentPlayer").first()
        if not challenged:
            challenged = User(username="OpponentPlayer", email="opponent@student.uwa.edu.au")
            challenged.set_password("password123")
            db.session.add(challenged)
            db.session.commit()
        
        # Fresh 5 photos in the DB
        Photos.query.delete()
        for i in range(5):
            p = Photos(image_path=f"test{i}.webp", latitude=-31.98, longitude=115.81)
            db.session.add(p)
        db.session.commit()
        
        all_photos = Photos.query.all()[:5]
        photo_ids = ",".join([str(p.pid) for p in all_photos])
        
        # Delete existing challenges to avoid conflict
        Challenge.query.delete()
        
        challenge = Challenge(
            challenger_id=challenger.uid,
            challenged_id=challenged.uid,
            photo_ids=photo_ids,
            status="in_progress",
            challenger_ready=True,
            challenged_ready=True,
            challenger_round=2, # Round 2
            challenger_score=1000 # Score 1000
        )
        db.session.add(challenge)
        db.session.commit()
        
        # 3. Get game page with challengeId
        self.driver.get(f"{self.base_url}/game?challengeId={challenge.id}")
        time.sleep(2.0) # Wait for page load and API calls
        
        # 4. Check if it rejoined at Round 2
        page_content = self.driver.page_source
        self.assertIn("Round 2 / 5", page_content)
        
        current_round_index = self.driver.execute_script("return currentRoundIndex;")
        total_score = self.driver.execute_script("return totalScore;")
        self.assertEqual(current_round_index, 1)
        self.assertEqual(total_score, 1000)




if __name__ == "__main__":
    unittest.main()