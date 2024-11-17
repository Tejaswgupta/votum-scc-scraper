import os
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from app import constants
from app.logger import logger

load_dotenv()

def scrap_aspxauth_cookie(url, enc):
    headers = {
        "Host": "www.scconline.com",
        "Content-Length": "0",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.118 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Sec-Ch-Ua": '"Not-A.Brand";v="99", "Chromium";v="124"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Referer": "https://www.scconline.com/",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Priority": "u=0, i",
    }

    response = requests.get(url + "/ApplicationLogin.aspx?enc=" + enc, headers=headers)
    ASPXAUTH = response.request.headers["Cookie"]

    return ASPXAUTH


def login_to_website(url, username, password):
    payload = {"loginId": username, "pass": password, "force": True}

    response = requests.get(url)
    x_access_token = response.cookies.get("x-access-token")

    soup = BeautifulSoup(response.content, "html.parser")
    list_containers = soup.find_all("script", type="text/javascript")
    crisp = list_containers[1].text.split("'")[3]

    cookie = {"x-access-token": x_access_token}
    headers = {
        "X-Access-Token": ".".join(x_access_token.split(".")[:-1]),
        "Vid": "league",
    }

    response = requests.post(
        url + "/home/login", data=payload, cookies=cookie, headers=headers
    )
    return response, crisp


def get_aspxauth():
    url = constants.BASE_URL
    username = os.getenv("SCC_USERNAME")
    password = os.getenv("SCC_PASSWORD")
    response, crisp = login_to_website(url, username, password)
    enc = response.json()["Url"].split("=")[1]
    return scrap_aspxauth_cookie(url, enc)


def periodically_update_aspxauth(interval, aspxauth_container):
    while True:
        aspxauth_container["ASPXAUTH"] = get_aspxauth()
        logger.info("ASPXAUTH updated to " + aspxauth_container["ASPXAUTH"])
        time.sleep(interval)



