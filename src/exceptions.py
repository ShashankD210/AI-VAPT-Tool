"""VAPT Tool - Custom exceptions"""
from dataclasses import dataclass, field


@dataclass
class VAPTException(Exception):
    message: str
    details: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


class ConfigError(VAPTException):
    pass


class ScanError(VAPTException):
    pass


class AuthenticationError(VAPTException):
    pass


class NetworkError(VAPTException):
    pass


class AIInferenceError(VAPTException):
    pass


class ReportingError(VAPTException):
    pass


class DatabaseError(VAPTException):
    pass
