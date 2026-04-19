# utils/session.py — logged-in user state
class UserSession:
    _user = None

    @classmethod
    def start(cls, user):
        cls._user = user

    @classmethod
    def end(cls):
        cls._user = None

    @classmethod
    def current(cls):
        return cls._user

    @classmethod
    def username(cls):
        return cls._user.username if cls._user else "Guest"

    @classmethod
    def is_logged_in(cls):
        return cls._user is not None
