import requests as req
from bs4 import BeautifulSoup as bs
import re

class EClass:
    base_url = 'https://eclass.ukdw.ac.id/'

    def __init__(self, nim: str, password: str):
        self.nim = nim
        self.password = password
        self.session = None

    def login(self) -> bool:
        session = req.Session()
        login_url = self.base_url + 'id/home/do_login'
        login = session.post(
            login_url,
            data = {
                'id': self.nim,
                'password': self.password
            }
        )
    
        soup = bs(login.text, 'html.parser')
        error = soup.find('div', {
            'id': 'error'
        })

        if error:
            return False

        self.session = session
        return True

    def create_session(self) -> req.Session:
        if not self.session:
            raise Exception("Login required. Please call the login method first.")
        return self.session