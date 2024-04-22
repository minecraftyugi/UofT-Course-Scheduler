import json
import math
import time
import requests
import urllib
from bs4 import BeautifulSoup, Tag
from threading import Thread
import pprint, re

BASE_URL = "https://degreeexplorer.utoronto.ca"

class DegreeExplorer:
    def __init__(self, username, password):
        self.session = requests.session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36"
        self.username = username
        self.password = password
        self._start()

    def _start(self):
        self._authenticate()

    def _authenticate(self):
        r = self.session.get(BASE_URL, verify=False)
        url = r.url
        data = {"$csrfToken.getParameterName()":"$csrfToken.getToken()",
                "_eventId_proceed":"",
                "j_username":self.username,
                "j_password":self.password}
        r = self.session.post(url, data=data)
        html = BeautifulSoup(r.text, "lxml")
        tag = html.find("input", attrs={"name":"SAMLResponse"})
        if tag:
            value = tag.get("value")
            url = BASE_URL + "/spACS"
            data = {"SAMLResponse":value}
            r = self.session.post(url, data=data)
            for resp in r.history:
                print(resp.status_code, resp.url)

            print(r.status_code, r.url)
            params = {"browser":"Unknown Browser"}
            url = BASE_URL + "/degreeExplorer/rest/dxMenu/getStudentUserData"
            self.session.get(url, params=params)
            self.session.headers["X-XSRF-TOKEN"] = self.session.cookies["XSRF-TOKEN"]

    def get_academic_history(self):
        url = BASE_URL + "/degreeExplorer/rest/dxStudent/getAcademicHistory"
        r = self.session.get(url)
        resp = r.json()
        return resp

if __name__ == "__main__":
    username = input("Username:").strip()
    password = input("Password:").strip()
    explorer = DegreeExplorer(username, password)
    print(explorer.get_academic_history())
