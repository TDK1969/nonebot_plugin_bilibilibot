from pydantic import BaseSettings
from typing import List

class Config(BaseSettings):
    # Your Config Here

    class Config:
        extra = "ignore"