# cookies.py - centralized cookie manager

import os
import pickle


def save_cookies(driver, filename):
    os.makedirs("cookies", exist_ok=True)
    filepath = os.path.join("cookies", filename)
    with open(filepath, "wb") as f:
        pickle.dump(driver.get_cookies(), f)


def load_cookies(driver, filename, domain_url):
    filepath = os.path.join("cookies", filename)
    if not os.path.exists(filepath):
        return False
    try:
        with open(filepath, "rb") as f:
            cookies = pickle.load(f)
        driver.get(domain_url)
        for cookie in cookies:
            cookie.pop("expiry", None)
            try:
                driver.add_cookie(cookie)
            except Exception:
                continue
        driver.get(domain_url)
        return True
    except Exception as e:
        print(f"⚠️ Failed to load cookies from {filename}: {e}")
        return False


def save_petfood_cookies(driver, path="petfood_cookies.pkl"):
    with open(path, "wb") as f:
        pickle.dump(driver.get_cookies(), f)


def load_petfood_cookies(driver, path="petfood_cookies.pkl"):
    if not os.path.exists(path):
        return False
    with open(path, "rb") as f:
        cookies = pickle.load(f)
    driver.get("https://orders.petfoodexperts.com/")
    for cookie in cookies:
        driver.add_cookie(cookie)
    return True


# Optional convenience wrappers


def save_orgill_cookies(driver):
    save_cookies(driver, "orgill.pkl")


def load_orgill_cookies(driver):
    return load_cookies(driver, "orgill.pkl", "https://www.orgill.com")


def save_petfood_experts_cookies(driver):
    save_cookies(driver, "petfood_experts.pkl")


def load_petfood_experts_cookies(driver):
    return load_cookies(driver, "petfood_experts.pkl", "https://www.petfoodexperts.com")


def save_phillips_cookies(driver):
    save_cookies(driver, "phillips.pkl")


def load_phillips_cookies(driver):
    return load_cookies(driver, "phillips.pkl", "https://www.phillipspet.com")
