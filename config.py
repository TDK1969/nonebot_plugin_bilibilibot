from pydantic import BaseSettings

class Config(BaseSettings):
    # Your Config Here
    #bili_db_name: str = "bilibili.db"

    class Config:
        extra = "ignore"