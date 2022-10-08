class BiliConnectionError(Exception):
    def __init__(self, target_type: int, target: str, reason: str):
        self.reason = reason
        self.target = target
        self.target_type = ["up主", "主播", "番剧", "短链接"][target_type]
    
    def __str__(self) -> str:
        return f"获取 {self.target_type} <{self.target}> 时发生网络错误: {self.reason}"

class BiliStatusCodeError(Exception):
    def __init__(self, target_type: int, target: str, status_code: int) -> None:
        '''网络连接状态码错误

        Args:
            target_type (int): 0-up;1-主播;2-番剧
            target (str): uid或season id
            status_code (int): 状态码
        '''
        self.status_code = status_code
        self.target = target
        self.target_type = ["up主", "主播", "番剧", "短链接"][target_type]
    
    def __str__(self) -> str:
        ret_str = f"获取 {self.target_type} <{self.target}> 时发生网络错误, 状态码为:{self.status_code}"
        return ret_str

class BiliAPIRetCodeError(Exception):
    def __init__(self, target_type: int, target: str, ret_code: int, ret_msg: str) -> None:
        '''_summary_

        Args:
            target_type (int): 0-up;1-主播;2-番剧
            target (str): uid或season id
            ret_code (int): b站接口返回的返回码
            msg (str): b站接口返回的错误信息

        Returns:
            _type_: _description_
        '''
        self.target = target
        self.target_type = ["up主", "主播", "番剧"][target_type]
        self.ret_code = ret_code
        self.ret_msg = ret_msg
        
    def __str__(self) -> str:
        ret_str = f"获取 {self.target_type} <{self.target}> 时接口返回错误\n接口错误码为:{self.ret_code}\n接口错误信息为:{self.ret_msg}"
        return ret_str

class BiliDatebaseError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
    
    def __str__(self) -> str:
        return self.reason

class BiliNoLiveRoom(Exception):
    def __init__(self, liver_name: str):
        self.ret_str = f"用户 <{liver_name}> 未开通直播间" 

    def __str__(self) -> str:
        return self.ret_str

class BiliAPI404Error(Exception):
    def __init__(self) -> None:
        pass

class BiliInvalidShortUrl(Exception):
    def __init__(self, short_url: str) -> None:
        self.short_url = short_url

class BiliInvalidRoomId(Exception):
    def __init__(self, room_id: str) -> None:
        self.room_id = room_id