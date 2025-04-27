import random
import os
import json
import re
from locust import HttpUser, task, between, tag
from faker import Faker

fake = Faker()

# Load test users from JSON file
TEST_USERS_PATH = os.path.join(os.path.dirname(__file__), 'test_users.json')
if os.path.exists(TEST_USERS_PATH):
    with open(TEST_USERS_PATH, 'r', encoding='utf-8') as f:
        TEST_USERS = json.load(f)
else:
    TEST_USERS = {"buyers": [], "designers": [], "factories": []}

def extract_csrf_token(html):
    match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\'](.+?)["\']', html)
    if match:
        return match.group(1)
    return None

class TextileWasteManagementUser(HttpUser):
    wait_time = between(1, 5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None
        self.user_id = None
        self.order_ids = []
        self.transaction_ids = []
        self.test_user = None
        self.csrf_token = None

    def on_start(self):
        self.pick_test_user()
        self.login()
        self.get_orders()
        self.get_transactions()

    def pick_test_user(self):
        if TEST_USERS["buyers"]:
            self.test_user = random.choice(TEST_USERS["buyers"])
        elif TEST_USERS["designers"]:
            self.test_user = random.choice(TEST_USERS["designers"])
        elif TEST_USERS["factories"]:
            self.test_user = random.choice(TEST_USERS["factories"])
        else:
            self.test_user = {"username": "", "password": ""}

    def get_csrf_token(self, url):
        response = self.client.get(url)
        if response.status_code == 200:
            token = extract_csrf_token(response.text)
            if token:
                # Also update cookies for csrftoken
                self.csrf_token = token
                return token
        return None

    def login(self):
        csrf_token = self.get_csrf_token("/accounts/login/")
        payload = {
            "username": self.test_user["username"],
            "password": self.test_user["password"],
            "csrfmiddlewaretoken": csrf_token
        }
        headers = {"Referer": self.client.base_url + "/accounts/login/"}
        cookies = {"csrftoken": csrf_token}
        with self.client.post("/accounts/login/", data=payload, headers=headers, cookies=cookies, catch_response=True) as response:
            if response.status_code in [200, 302]:
                self.token = "demo-token"
                self.user_id = random.randint(1000, 9999)
            else:
                response.failure(f"Failed to log in: {response.status_code}")

    def get_orders(self):
        with self.client.get("/orders/", catch_response=True) as response:
            if response.status_code == 200:
                self.order_ids = [f"ORDER-{random.randint(1000, 9999)}" for _ in range(3)]
            else:
                response.failure(f"Failed to get orders: {response.status_code}")

    def get_transactions(self):
        with self.client.get("/transactions/", catch_response=True) as response:
            if response.status_code == 200:
                self.transaction_ids = [f"TXN-{random.randint(1000, 9999)}" for _ in range(3)]
            else:
                response.failure(f"Failed to get transactions: {response.status_code}")

    @tag("order_submission")
    @task(3)
    def create_order(self):
        csrf_token = self.get_csrf_token("/orders/create/")
        payload = {
            "design_id": f"DESIGN-{random.randint(1000, 9999)}",
            "quantity": random.randint(10, 100),
            "special_instructions": fake.text(max_nb_chars=100),
            "delivery_address": fake.address(),
            "contact_phone": fake.phone_number(),
            "csrfmiddlewaretoken": csrf_token
        }
        headers = {"Referer": self.client.base_url + "/orders/create/"}
        cookies = {"csrftoken": csrf_token}
        with self.client.post("/orders/create/", data=payload, headers=headers, cookies=cookies, catch_response=True) as response:
            if response.status_code in [200, 302]:
                new_order_id = f"ORDER-{random.randint(1000, 9999)}"
                self.order_ids.append(new_order_id)
            else:
                response.failure(f"Failed to create order: {response.status_code}")

    @tag("view_transactions")
    @task(5)
    def view_transactions(self):
        with self.client.get("/transactions/", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Failed to view transaction list: {response.status_code}")

    @tag("view_transaction_details")
    @task(2)
    def view_transaction_detail(self):
        if not self.transaction_ids:
            return
        transaction_id = random.choice(self.transaction_ids)
        with self.client.get(f"/transactions/{transaction_id}/", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Failed to view transaction details: {response.status_code}")

    @tag("view_order_details")
    @task(2)
    def view_order_detail(self):
        if not self.order_ids:
            return
        order_id = random.choice(self.order_ids)
        with self.client.get(f"/orders/{order_id}/", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Failed to view order details: {response.status_code}")

    @tag("view_stats")
    @task(1)
    def view_transaction_stats(self):
        with self.client.get("/transactions/stats/", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Failed to view transaction stats: {response.status_code}")