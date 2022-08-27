class BiliConnectionError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
    
    def __str__(self) -> str:
        return self.reason

class BiliDatebaseError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
    
    def __str__(self) -> str:
        return self.reason
