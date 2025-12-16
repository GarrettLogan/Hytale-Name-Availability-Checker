import csv
import time
from urllib.parse import urlparse, parse_qs
import requests
import os

HYTALE_EMAIL = "" # Enter your Hytale Email Here
HYTALE_PASSWORD = "" # Enter your Hytale Password here

LOGIN_URL = "https://backend.accounts.hytale.com/self-service/login/browser"
USERNAME_CHECK_URL = "https://accounts.hytale.com/api/account/username-reservations/availability?username={}"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/ "
                  "(KHTML, like Gecko) Chrome/ Safari/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}) # Get your own headers and place here This is an example


# ---------- Login function ----------
def login():
    # Step 1: Get login flow
    resp = session.get(LOGIN_URL, allow_redirects=False)
    if resp.status_code not in (302, 303):
        raise Exception(f"Failed to get login flow URL, status: {resp.status_code}")

    location = resp.headers.get("Location")
    if not location:
        raise Exception("No Location header found in login init response")

    parsed = urlparse(location)
    flow_id = parse_qs(parsed.query).get("flow", [None])[0]
    if not flow_id:
        raise Exception("No flow ID found in redirect URL")

    # Step 2: Extract CSRF token from cookies
    csrf_token = None
    for cookie in session.cookies:
        if cookie.name.startswith("csrf_token"):
            csrf_token = cookie.value
            break
    if not csrf_token:
        raise Exception("CSRF token not found in cookies")

    # Step 3: Submit login
    data = {
        "csrf_token": csrf_token,
        "identifier": HYTALE_EMAIL,
        "password": HYTALE_PASSWORD,
        "method": "password"
    }
    login_service_url = f"https://backend.accounts.hytale.com/self-service/login?flow={flow_id}"
    login_response = session.post(login_service_url, data=data, allow_redirects=False)

    if login_response.status_code != 303 or "/settings" not in login_response.headers.get("Location", ""):
        raise Exception(f"Login failed: {login_response.status_code} - {login_response.text[:200]}")

    # Step 4: Follow redirect to finalize session
    session.get(login_response.headers["Location"], allow_redirects=True)
    print("Login successful!")


# ---------- Username check function ----------
def check_username(username):
    url = USERNAME_CHECK_URL.format(username)
    resp = session.get(url)
    if resp.status_code == 200:
        return True  # Available
    elif resp.status_code == 400:
        return False  # Taken
    else:
        raise Exception(f"Hytale API error: {resp.status_code}")



# ---------- Main script ----------
if __name__ == "__main__":
    if not HYTALE_EMAIL or not HYTALE_PASSWORD:
        raise Exception("Set HYTALE_EMAIL and HYTALE_PASSWORD environment variables before running.")

    login()

    # ---------- Enter Names here separated by comma "", "", "" ----------
    test_names = [
        ""
    ]

    with open("hytale_usernames.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Username", "Status"])

        for name in test_names:
            try:
                available = check_username(name)
                status = "Available" if available else "Taken"
                print(f"{name}: {status}")
                writer.writerow([name, status])
            except Exception as e:
                print(f"{name}: {e}")
                writer.writerow([name, "⚠ Error"])
                if "429" in str(e):
                    print("Rate limit reached, waiting 60s...")
                    time.sleep(60)
            time.sleep(1)  # avoid rate limiting
