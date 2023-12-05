from requests import Session

from .models.app import App

class Heroku:
    _session: Session

    def apps(self) -> list[App]: ...
    def app(self, id_or_name: str) -> App: ...
