"""Общие расширения, вынесенные сюда во избежание циклических импортов."""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
