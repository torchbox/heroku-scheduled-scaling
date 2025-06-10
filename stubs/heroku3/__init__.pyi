from requests import Session

from .core import Heroku

def from_key(api_key: str, session: Session) -> Heroku: ...
