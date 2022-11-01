from typing import List
from .db import bili_database
from .exception import BiliDatebaseError
from nonebot.log import logger


class BiliTaskManager():
    def __init__(self) -> None:
        self.up_list = dict()
        self.liver_list = dict()
        self.telegram_list = dict()
        self.dynamic_list = dict()

        self.user_follower_list = dict()
        self.group_follower_list = dict()
    
        self.__up_update_check_ptr__ = 0
        self.__dynamic_update_check_ptr__ = 0

        self.__update_check_len__ = 8

        self.__init_from_database__()
        

    def __init_from_database__(self):
        '''从数据库中进行初始化
        '''
        i = 0
        try:
            up_list = bili_database.query_all(0)
            for up_uid, up_name, latest_timestamp in up_list:
                self.up_list[up_uid] = {
                    "uid": up_uid,
                    "up_name": up_name, 
                    "latest_timestamp": latest_timestamp,
                    "user_follower": set(bili_database.query_user_relation(0, up_uid)),
                    "group_follower": set(bili_database.query_group_relation(0, up_uid))
                }
                if not self.up_list[up_uid]["user_follower"] and not self.up_list[up_uid]["group_follower"]:
                    self.up_list.pop(up_uid)
                    logger.debug(f'{up_uid}已经无人关注')
                else:
                    self.up_list[up_uid]["next_update_check"] = i
                i = (i + 1) % self.__update_check_len__
                    
            liver_list = bili_database.query_all(1)
            for liver_uid, liver_name, is_live, room_id in liver_list:
                self.liver_list[liver_uid] = {
                    "liver_uid": liver_uid, 
                    "liver_name": liver_name,
                    "is_live": is_live,
                    "room_id": room_id,
                    "user_follower": set(bili_database.query_user_relation(2, liver_uid)),
                    "group_follower": set(bili_database.query_group_relation(2, liver_uid))
                }
                if not self.liver_list[liver_uid]["user_follower"] and not self.liver_list[liver_uid]["group_follower"]:
                    self.liver_list.pop(liver_uid)
                    logger.debug(f'{liver_uid}已经无人关注')
                
            telegram_list = bili_database.query_all(2)
            for season_id, telegram_title, episode in telegram_list:
                self.telegram_list[season_id] = {
                    "season_id": season_id,
                    "telegram_title": telegram_title,
                    "episode": episode,
                    "user_follower": set(bili_database.query_user_relation(4, season_id)),
                    "group_follower": set(bili_database.query_group_relation(4, season_id))
                }
                if not self.telegram_list[season_id]["user_follower"] and not self.telegram_list[season_id]["group_follower"]:
                    self.telegram_list.pop(season_id)
                    logger.debug(f'{season_id}已经无人关注')
            
            dynamic_list = bili_database.query_all(5)
            for uid, u_name, pin_id_str, latest_timestamp in dynamic_list:
                self.dynamic_list[uid] = {
                    "uid": uid,
                    "u_name": u_name,
                    "pin_id_str": pin_id_str,
                    "latest_timestamp": latest_timestamp,
                    "user_follower": set(bili_database.query_user_relation(6, uid)),
                    "group_follower": set(bili_database.query_group_relation(6, uid))
                }
                if not self.dynamic_list[uid]["user_follower"] and not self.dynamic_list[uid]["group_follower"]:
                    self.dynamic_list.pop(uid)
                    logger.debug(f'{uid}已经无人关注')
                else:
                    self.dynamic_list[uid]["next_update_check"] = i
                i = (i + 1) % self.__update_check_len__

                
                    

        except Exception as e:
            logger.debug(f'{e}')
            
            logger.error(f'初始化任务管理器失败')
    
    def get_up_check_update_list(self) -> List[str]:
        '''每次触发检查更新的up主

        Returns:
            List[str]: 应检查更新的up和时间戳的列表
        '''
        check_update_list = []
        for up_uid in self.up_list.keys():
            if self.up_list[up_uid]["next_update_check"] == self.__up_update_check_ptr__:
                check_update_list.append(up_uid)
        self.__up_update_check_ptr__ = (self.__up_update_check_ptr__ + 1) % self.__update_check_len__
        return check_update_list
    
    def get_dynamic_check_update_list(self) -> List[str]:
        '''每次触发检查更新的动态

        Returns:
            List[str]: 应检查更新动态主的uid
        '''
        check_update_list = []
        for uid in self.dynamic_list.keys():
            if self.dynamic_list[uid]["next_update_check"] == self.__dynamic_update_check_ptr__:
                check_update_list.append(uid)
        self.__dynamic_update_check_ptr__ = (self.__dynamic_update_check_ptr__ + 1) % self.__update_check_len__
        return check_update_list
    
    def update_up_info(self, up_uid: str, latest_timestamp: int) -> bool:
        '''更新任务管理器以及数据库中的up信息

        Args:
            up_uid (str): up的uid
            latest_timestamp (int): 最新视频时间戳

        Returns:
            bool: 是否成功
        '''
        try:
            bili_database.update_info(0, latest_timestamp, up_uid)
            self.up_list[up_uid]["latest_timestamp"] = latest_timestamp
            return True
        except BiliDatebaseError as e:
            exception_msg = f'【错误报告】\n更新主播 <{up_uid}> 时数据库发生错误\n错误信息: {e}\n'
            logger.error(exception_msg)
            return False
    
    def update_liver_info(self, liver_uid: str, is_live: bool) -> bool:
        '''更新任务管理器以及数据库中的主播信息

        Args:
            liver_uid (str): 主播的uid
            is_live (int): 是否直播

        Returns:
            bool: 是否成功
        '''
        try:
            bili_database.update_info(1, is_live, liver_uid)
            self.liver_list[liver_uid]["is_live"] = is_live
            return True
        except BiliDatebaseError as e:
            exception_msg = f'【错误报告】\n更新主播 <{liver_uid}> 时数据库发生错误\n错误信息: {e}\n'
            logger.error(exception_msg)
            return False
    
    def update_telegram_info(self, season_id: str, episode: int, is_finish: bool) -> bool:
        '''更新任务管理器以及数据库中的番剧信息

        Args:
            season_id (str): season_id
            episode (int): 最新集数
            is_finish (bool): 是否完结

        Returns:
            bool: 是否成功
        '''
        try:
            bili_database.update_info(2, episode, is_finish, season_id)
            if is_finish:
                self.telegram_list.pop(season_id)
            else:
                self.telegram_list[season_id]["episode"] = episode
            return True
        except BiliDatebaseError as e:
            exception_msg = f'【错误报告】\n更新番剧 <{season_id}> 时数据库发生错误\n错误信息: {e}\n'
            logger.error(exception_msg)
            return False
    
    def update_dynamic_pin_id(self, uid: str, pin_id_str: str) -> bool:
        '''更新任务管理器以及数据库中的动态主的置顶id

        Args:
            uid (str): 动态主的uid
            pin_id_str (str): 置顶动态的id

        Returns:
            bool: 是否成功
        '''
        try:
            bili_database.update_info(3, pin_id_str, uid)
            self.dynamic_list[uid]["pin_id_str"] = pin_id_str
            return True
        except BiliDatebaseError as e:
            exception_msg = f'【错误报告】\n更新动态主 <{uid}> 时数据库发生错误\n错误信息: {e}\n'
            logger.error(exception_msg)
            return False
    
    def update_dynamic_latest_timestamp(self, uid: str, latest_timestamp: int) -> bool:
        '''更新任务管理器以及数据库中的动态主的最新动态时间戳

        Args:
            uid (str): 动态主的uid
            latest_timestamp (int): 最新动态的时间戳

        Returns:
            bool: 是否成功
        '''
        try:
            bili_database.update_info(4, latest_timestamp, uid)
            self.dynamic_list[uid]["latest_timestamp"] = latest_timestamp
            return True
        except BiliDatebaseError as e:
            exception_msg = f'【错误报告】\n更新动态主 <{uid}> 时数据库发生错误\n错误信息: {e}\n'
            logger.error(exception_msg)
            return False

    def add_user_follower(self, target_type: int, target_id: str, user_id: str) -> bool:
        '''_summary_

        Args:
            target_type (int): 0-up主;1-主播;2-番剧;3-动态
            target_id (str): up主/主播/番剧/动态主的id 
            user_id (str): 关注者的id

        Returns:
            bool: 是否成功
        '''
        # 写入数据库,如果不存在于缓存,则从数据库写入缓存
        try:
            bili_database.insert_relation(2 * target_type, target_id, user_id)

            if target_type == 0:
                if target_id not in self.up_list:
                    _, up_name, latest_timestamp = bili_database.query_info(2, target_id)
                    self.up_list[target_id] = {
                        "uid": target_id,
                        "up_name": up_name, 
                        "latest_timestamp": latest_timestamp,
                        "user_follower": set(bili_database.query_user_relation(0, target_id)),
                        "group_follower": set(bili_database.query_group_relation(0, target_id)),
                        "next_update_check": self.__up_update_check_ptr__
                    }
                else:
                    self.up_list[target_id]["user_follower"].add(user_id)
            elif target_type == 1 :
                if target_id not in self.liver_list:
                    _, liver_name, is_live, room_id = bili_database.query_info(3, target_id)
                    self.liver_list[target_id] = {
                        "liver_uid": target_id, 
                        "liver_name": liver_name,
                        "is_live": is_live,
                        "room_id": room_id,
                        "user_follower": set(bili_database.query_user_relation(2, target_id)),
                        "group_follower": set(bili_database.query_group_relation(2, target_id))
                    }
                else:
                    self.liver_list[target_id]["user_follower"].add(user_id)
            elif target_type == 2:
                if target_id not in self.telegram_list:
                    _, telegram_title, episode = bili_database.query_info(4, target_id)
                    self.telegram_list[target_id] = {
                        "season_id": target_id,
                        "telegram_title": telegram_title,
                        "episode": episode,
                        "user_follower": set(bili_database.query_user_relation(4, target_id)),
                        "group_follower": set(bili_database.query_group_relation(4, target_id))
                    }
                else:
                    self.telegram_list[target_id]["user_follower"].add(user_id)
            elif target_type == 3:
                if target_id not in self.dynamic_list:
                    _, u_name, pin_id_str, latest_timestamp = bili_database.query_info(5, target_id)
                    self.dynamic_list[target_id] = {
                        "uid": target_id,
                        "u_name": u_name,
                        "pin_id_str": pin_id_str,
                        "latest_timestamp": latest_timestamp,
                        "next_update_check": self.__dynamic_update_check_ptr__,
                        "user_follower": set(bili_database.query_user_relation(6, target_id)),
                        "group_follower": set(bili_database.query_group_relation(6, target_id))
                }
                else:
                    self.dynamic_list[target_id]["user_follower"].add(user_id)
            
            return True
        except BiliDatebaseError as e:
            exception_msg = f'【错误报告】\n用户<{user_id}>关注<{target_id}>时数据库发生错误\n错误信息: {e}\n'
            logger.error(exception_msg)
            return False

    def add_group_follower(self, target_type: int, target_id: str, group_id: str) -> bool:
        '''_summary_

        Args:
            target_type (int): 0-up主;1-主播;2-番剧;3-动态
            target_id (str): up主/主播/番剧/动态主的id 
            group_id (str): 关注群的id

        Returns:
            bool: 是否成功
        '''
        # 写入数据库,如果不存在于缓存,则从数据库写入缓存
        try:
            bili_database.insert_relation(2 * target_type + 1, target_id, group_id)

            if target_type == 0:
                if target_id not in self.up_list:
                    _, up_name, latest_timestamp = bili_database.query_info(2, target_id)
                    self.up_list[target_id] = {
                        "uid": target_id,
                        "up_name": up_name, 
                        "latest_timestamp": latest_timestamp,
                        "next_update_check": self.__up_update_check_ptr__,
                        "user_follower": set(bili_database.query_user_relation(0, target_id)),
                        "group_follower": set(bili_database.query_group_relation(0, target_id))
                    }
                else:
                    self.up_list[target_id]["group_follower"].add(group_id)
            elif target_type == 1 :
                if target_id not in self.liver_list:
                    _, liver_name, is_live, room_id = bili_database.query_info(3, target_id)
                    self.liver_list[target_id] = {
                        "liver_uid": target_id, 
                        "liver_name": liver_name,
                        "is_live": is_live,
                        "room_id": room_id,
                        "user_follower": set(bili_database.query_user_relation(2, target_id)),
                        "group_follower": set(bili_database.query_group_relation(2, target_id))
                    }
                else:
                    self.liver_list[target_id]["group_follower"].add(group_id)
            elif target_type == 2:
                if target_id not in self.telegram_list:
                    _, telegram_title, episode = bili_database.query_info(4, target_id)
                    self.telegram_list[target_id] = {
                        "season_id": target_id,
                        "telegram_title": telegram_title,
                        "episode": episode,
                        "user_follower": set(bili_database.query_user_relation(4, target_id)),
                        "group_follower": set(bili_database.query_group_relation(4, target_id))
                    }
                else:
                    self.telegram_list[target_id]["group_follower"].add(group_id)
            elif target_type == 3:
                if target_id not in self.dynamic_list:
                    _, u_name, pin_id_str, latest_timestamp = bili_database.query_info(5, target_id)
                    self.dynamic_list[target_id] = {
                        "uid": target_id,
                        "u_name": u_name,
                        "pin_id_str": pin_id_str,
                        "latest_timestamp": latest_timestamp,
                        "next_update_check": self.__dynamic_update_check_ptr__,
                        "user_follower": set(bili_database.query_user_relation(6, target_id)),
                        "group_follower": set(bili_database.query_group_relation(6, target_id))
                    }
                else:
                    self.dynamic_list[target_id]["group_follower"].add(group_id)
            return True
        except BiliDatebaseError as e:
            exception_msg = f'【错误报告】\n群<{group_id}>关注<{target_id}>时数据库发生错误\n错误信息: {e}\n'
            logger.error(exception_msg)
            return False
    
    def remove_user_follower(self, target_type: int, target_id: str, user_id: str) -> bool:
        '''移除个人用户的关注

        Args:
            target_type (int): 0-up主/1-主播/2-番剧/3-动态
            target_id (str): up主/主播/番剧的id 
            user_id (str): 关注者的id

        Returns:
            bool: 是否成功
        '''
        try:
            bili_database.delete_relation(target_type * 2, user_id, target_id)
            if target_type == 0:
                self.up_list[target_id]["user_follower"].remove(user_id)
                if not self.up_list[target_id]["user_follower"] and not self.up_list[target_id]["group_follower"]:
                    self.up_list.pop(target_id)
                    logger.debug(f'{target_id}已经无人关注')
            elif target_type == 1:
                self.liver_list[target_id]["user_follower"].remove(user_id)
                if not self.liver_list[target_id]["user_follower"] and not self.liver_list[target_id]["group_follower"]:
                    self.liver_list.pop(target_id)
                    logger.debug(f'{target_id}已经无人关注')
            elif target_type == 2:
                self.telegram_list[target_id]["user_follower"].remove(user_id)
                if not self.telegram_list[target_id]["user_follower"] and not self.telegram_list[target_id]["group_follower"]:
                    self.telegram_list.pop(target_id)
                    logger.debug(f'{target_id}已经无人关注')
            elif target_type == 3:
                self.dynamic_list[target_id]["user_follower"].remove(user_id)
                if not self.dynamic_list[target_id]["user_follower"] and not self.dynamic_list[target_id]["group_follower"]:
                    self.dynamic_list.pop(target_id)
                    logger.debug(f'{target_id}已经无人关注')
        except BiliDatebaseError as e:
            exception_msg = f'【错误报告】\n用户<{user_id}>取关<{target_id}>时数据库发生错误\n错误信息: {e}\n'
            logger.error(exception_msg)
            return False
    
    def remove_group_follower(self, target_type: int, target_id: str, group_id: str) -> bool:
        '''移除个人用户的关注

        Args:
            target_type (int): 0-up主/1-主播/2-番剧/3-动态
            target_id (str): up主/主播/番剧的id 
            group_id (str): 关注者的id

        Returns:
            bool: 是否成功
        '''
        try:
            bili_database.delete_relation(target_type * 2 + 1, group_id, target_id)
            if target_type == 0:
                self.up_list[target_id]["group_follower"].remove(group_id)
                if not self.up_list[target_id]["user_follower"] and not self.up_list[target_id]["group_follower"]:
                    self.up_list.pop(target_id)
                    logger.debug(f'{target_id}已经无人关注')
            elif target_type == 1:
                self.liver_list[target_id]["group_follower"].remove(group_id)
                if not self.liver_list[target_id]["user_follower"] and not self.liver_list[target_id]["group_follower"]:
                    self.liver_list.pop(target_id)
                    logger.debug(f'{target_id}已经无人关注')
            elif target_type == 2:
                self.telegram_list[target_id]["group_follower"].remove(group_id)
                if not self.telegram_list[target_id]["user_follower"] and not self.telegram_list[target_id]["group_follower"]:
                    self.telegram_list.pop(target_id)
                    logger.debug(f'{target_id}已经无人关注')
            elif target_type == 3:
                self.dynamic_list[target_id]["group_follower"].remove(group_id)
                if not self.dynamic_list[target_id]["user_follower"] and not self.dynamic_list[target_id]["group_follower"]:
                    self.dynamic_list.pop(target_id)
                    logger.debug(f'{target_id}已经无人关注')
        except BiliDatebaseError as e:
            exception_msg = f'【错误报告】\n群<{group_id}>取关<{target_id}>时数据库发生错误\n错误信息: {e}\n'
            logger.error(exception_msg)
            return False

    def add_up_info(self, up_uid: str, up_name: str, latest_timestamp: int) -> bool:
        '''向任务管理器以及数据库中增加up信息

        Args:
            up_uid (str): up的uid
            up_name (str): up的用户名
            latest_timestamp (int): 最新视频的时间戳

        Returns:
            bool: 是否成功
        '''
        try:
            if not bili_database.query_info(2, up_uid):
                bili_database.insert_info(2, up_uid, up_name, latest_timestamp)
            self.up_list[up_uid] = {
                "uid": up_uid,
                "up_name": up_name, 
                "latest_timestamp": latest_timestamp,
                "user_follower": set(bili_database.query_user_relation(0, up_uid)),
                "group_follower": set(bili_database.query_group_relation(0, up_uid)),
                "next_update_check": self.__up_update_check_ptr__
            }
            return True
        except BiliDatebaseError as e:
            exception_msg = f'【错误报告】\n创建up主<{up_uid}>信息时数据库发生错误\n错误信息: {e}\n'
            logger.error(exception_msg)
            return False
    
    def add_liver_info(self, liver_uid: str, liver_name: str, is_live: bool, room_id: str) -> bool:
        '''向任务管理器以及数据库中增加主播信息

        Args:
            liver_uid (str): 主播的uid
            liver_name (str): 主播的用户名
            is_live (bool): 是否正在直播
            room_id (str): 房间id

        Returns:
            bool: 是否成功
        '''
        try:
            if not bili_database.query_info(3, liver_uid):
                bili_database.insert_info(3, liver_uid, liver_name, is_live, room_id)
            self.liver_list[liver_uid] = {
                "liver_uid": liver_uid, 
                "liver_name": liver_name,
                "is_live": is_live,
                "room_id": room_id,
                "user_follower": set(bili_database.query_user_relation(2, liver_uid)),
                "group_follower": set(bili_database.query_group_relation(2, liver_uid))
            }
            return True
        except BiliDatebaseError as e:
            exception_msg = f'【错误报告】\n创建主播<{liver_uid}>信息时数据库发生错误\n错误信息: {e}\n'
            logger.error(exception_msg)
            return False
    
    def add_telegram_info(self, season_id: str, telegram_title: str, episode: int, is_finish: bool) -> bool:
        '''向任务管理器以及数据库中增加番剧信息

        Args:
            season_id (str): 番剧的season_id
            telegram_title (str): 番剧名
            episode (int): 最新集数
            is_finish (bool): 是否完结

        Returns:
            bool: 是否成功
        '''
        try:
            if not bili_database.query_info(4, season_id): 
                bili_database.insert_info(4, season_id, telegram_title, episode, is_finish)
            self.telegram_list[season_id] = {
                "season_id": season_id,
                "telegram_title": telegram_title,
                "episode": episode,
                "user_follower": set(bili_database.query_user_relation(4, season_id)),
                "group_follower": set(bili_database.query_group_relation(4, season_id))
            }
            return True
        except BiliDatebaseError as e:
            exception_msg = f'【错误报告】\n创建番剧<{season_id}>信息时数据库发生错误\n错误信息: {e}\n'
            logger.error(exception_msg)
            return False
    
    def add_dynamic_info(self, uid: str, u_name: str, pin_id_str: str, latest_timestamp: int) -> bool:
        '''向任务管理器以及数据库中增加动态主信息

        Args:
            uid (str): uid
            u_name (str): 动态主的用户名
            pin_id_str (str): 置顶动态的id
            latest_timestamp (int): 最新动态的时间戳

        Returns:
            bool: 是否成功
        '''
        try:
            if not bili_database.query_info(5, uid):
                bili_database.insert_info(5, uid, u_name, pin_id_str, latest_timestamp)
            self.dynamic_list[uid] = {
                "uid": uid,
                "u_name": u_name,
                "pin_id_str": pin_id_str,
                "latest_timestamp": latest_timestamp,
                "next_update_check": self.__dynamic_update_check_ptr__,
                "user_follower": set(bili_database.query_user_relation(6, uid)),
                "group_follower": set(bili_database.query_group_relation(6, uid))
            }
            logger.debug(f'in add_dynamic_info {self.dynamic_list[uid]}')
            
            return True
        except BiliDatebaseError as e:
            exception_msg = f'【错误报告】\n创建动态主<{uid}>信息时数据库发生错误\n错误信息: {e}\n'
            logger.error(exception_msg)
            return False
            

bili_task_manager = BiliTaskManager()
logger.debug(f' bili task manager - up_list = {bili_task_manager.up_list}')
logger.debug(f' bili task manager - liver_list = {bili_task_manager.liver_list}')
logger.debug(f' bili task manager - telegram_list = {bili_task_manager.telegram_list}')
logger.debug(f' bili task manager - dynamic_list = {bili_task_manager.dynamic_list}')

            




