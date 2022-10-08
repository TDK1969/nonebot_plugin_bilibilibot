import sqlite3
from typing import List, Tuple
import os
import json
from nonebot.log import logger
from os.path import abspath, dirname
from nonebot import get_driver
from .config import Config
from .exception import *
global_config = get_driver().config
config = Config.parse_obj(global_config)
__PLUGIN_NAME = "[bilibilibot~数据库]"

class BiliDatabase():
    def __init__(self) -> None:
        # 需要从config中获得
        self.db_name = dirname(abspath(__file__)) + "/bilibili_2.db"
        self.conn = sqlite3.connect(self.db_name)
        self.init_database()
    
    def init_database(self) -> None:
        '''初始化数据库,如果不存在表则创建

        '''
        cur = self.conn.cursor()
        logger.debug(f'初始化数据库')
        
        #创建up表   
        cur.execute('''CREATE TABLE IF NOT EXISTS up
            (
                up_uid VARCHAR(20) PRIMARY KEY NOT NULL,
                up_name VARCHAR(50) NOT NULL,
                latest_update INT NOT NULL
            )
            ''')

        # 创建liver表
        cur.execute('''CREATE TABLE IF NOT EXISTS liver
            (
                liver_uid VARCHAR(20) PRIMARY KEY NOT NULL,
                liver_name VARCHAR(50) NOT NULL,
                is_live TINYINT(1) DEFAULT 0 NOT NULL,
                live_room VARCHAR(30) NOT NULL
            )
            ''')

        # 创建telegram表
        cur.execute('''CREATE TABLE IF NOT EXISTS telegram
            (
                season_id VARCHAR(20) PRIMARY KEY NOT NULL,
                telegram_title VARCHAR(50) NOT NULL,
                episode INT NOT NULL,
                is_finish TINYINT(1) DEFAULT 0 NOT NULL
            )
            ''')

        # 创建个人用户表
        cur.execute('''CREATE TABLE IF NOT EXISTS qq_user
            (
                user_id VARCHAR(20) PRIMARY KEY NOT NULL,
                user_name VARCHAR(50) NOT NULL
            )
            ''')

        # 创建群用户表
        cur.execute('''CREATE TABLE IF NOT EXISTS qq_group
            (
                group_id VARCHAR(20) PRIMARY KEY NOT NULL,
                group_name VARCHAR(50) NOT NULL
            )
            ''')

        # 创建关注up表
        cur.execute('''CREATE TABLE IF NOT EXISTS up_follower
            (
                id INTERGER PRIMARY KEY,
                up_uid VARCHAR(20) NOT NULL,
                user_id VARCHAR(20),
                group_id VARCHAR(20)
            )
            ''')

        # 创建索引
        cur.execute("CREATE INDEX IF NOT EXISTS up_index ON up_follower (up_uid)")
        cur.execute("CREATE INDEX IF NOT EXISTS up_user_index ON up_follower (user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS up_group_index ON up_follower (group_id)")

        # 创建关注主播表
        cur.execute('''CREATE TABLE IF NOT EXISTS liver_follower
            (
                id INTERGER PRIMARY KEY,
                liver_uid VARCHAR(20) NOT NULL,
                user_id VARCHAR(20),
                group_id VARCHAR(20)
            )
            ''')

        # 创建索引
        cur.execute("CREATE INDEX IF NOT EXISTS liver_index ON liver_follower (liver_uid)")
        cur.execute("CREATE INDEX IF NOT EXISTS liver_user_index ON liver_follower (user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS liver_group_index ON liver_follower (group_id)")

        # 创建关注节目表
        cur.execute('''CREATE TABLE IF NOT EXISTS telegram_follower
            (
                id INTERGER PRIMARY KEY,
                season_id VARCHAR(20) NOT NULL,
                user_id VARCHAR(20),
                group_id VARCHAR(20)
            )
            ''')

        # 创建索引
        cur.execute("CREATE INDEX IF NOT EXISTS tele_index ON telegram_follower (season_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS tele_user_index ON telegram_follower (user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS tele_group_index ON telegram_follower (group_id)")

        logger.debug(f'数据库初始化完毕')
        
        cur.close()
        self.conn.commit()

    def insert_info(self, sql_type: int, *args) -> bool:
        '''插入信息表的通用操作

        Args:
            type (int): 0-用户;1-群组;2-up;3-主播;4-番剧
            args: 
                0-用户:   user_id, user_name
                1-群组:   group_id, group_name
                2-up主:   up_uid, up_name, latest_update
                3-主播:   liver_uid, liver_name, is_live, live_room
                4-番剧:   season_id, telegram_title, episode, is_finish

        Returns:
            bool: 是否成功
        '''
        cur = self.conn.cursor()

        sqls = [
            "INSERT INTO qq_user(user_id, user_name) VALUES (?, ?)",
            "INSERT INTO qq_group(group_id, group_name) VALUES (?, ?)",
            "INSERT INTO up(up_uid, up_name, latest_update) VALUES (?, ?, ?)",
            "INSERT INTO liver(liver_uid, liver_name, is_live, live_room) VALUES (?, ?, ?, ?)",
            "INSERT INTO telegram(season_id, telegram_title, episode, is_finish) VALUES (?, ?, ?, ?)"
        ]
        #logger.info(f'信息表进行插入')
        
        try:
            cur.execute(sqls[sql_type], args)
        except Exception as e:
            ##logger.error(f'[]插入信息表时发生错误:\n{e}')
            self.conn.rollback()
            cur.close()
            raise BiliDatebaseError(f"数据库插入信息表时发生错误:{e.args[0]}")
        else:
            cur.close()
            self.conn.commit()
            #logger.info(f'插入信息表成功')
            return True
        
    def insert_relation(self, sql_type: int, uid: str, follower_id: str) -> bool:
        '''插入关注表

        Args:
            type (int): 0-个人关注up;1-群关注up;2-个人关注主播;3-群关注主播;4-个人关注番剧;5-群关注番剧
            uid (str): 被关注者的id
            follower_id (str): 粉丝的id

        Returns:
            bool: 是否成功
        '''

        sqls = [
            "INSERT INTO up_follower(id, up_uid, user_id) VALUES (NULL, ?, ?)",
            "INSERT INTO up_follower(id, up_uid, group_id) VALUES (NULL, ?, ?)",
            "INSERT INTO liver_follower(id, liver_uid, user_id)  VALUES (NULL, ?, ?)",
            "INSERT INTO liver_follower(id, liver_uid, group_id) VALUES (NULL, ?, ?)",
            "INSERT INTO telegram_follower(id, season_id, user_id) VALUES (NULL, ?, ?)",
            "INSERT INTO telegram_follower(id, season_id, group_id) VALUES (NULL, ?, ?)",
        ]
        cur = self.conn.cursor()
        
        assert 0 <= sql_type < 6, "索引长度错误"
        #logger.info(f'关注表进行插入')
        try:
            cur.execute(sqls[sql_type], (uid, follower_id))
        except Exception as e:
            ##logger.error(f'插入关注表时发生错误:\n{e}')
            cur.close()
            self.conn.rollback()
            raise BiliDatebaseError(f"数据库插入关注表时发生错误:{e.args[0]}")
        else:
            #logger.info(f'插入关注表成功')
            cur.close()
            self.conn.commit()
            return True
            
    def query_info(self, sql_type: int, target_id: str) -> Tuple:
        '''查询信息表通用操作

        Args:
            sql_type (int): 0-用户;1-群组;2-up;3-主播;4-番剧
            target_id (str): up/主播/番剧/用户/群的id

        Returns:
            Tuple: 查询结果
        '''
        cur = self.conn.cursor()
        sqls = [
            "SELECT user_id, user_name FROM qq_user WHERE user_id = ?",
            "SELECT group_id, group_name FROM qq_group WHERE group_id = ?",
            "SELECT up_uid, up_name, latest_update FROM up WHERE up_uid = ?",
            "SELECT liver_uid, liver_name, is_live, live_room FROM liver WHERE liver_uid = ?",
            "SELECT season_id, telegram_title, episode FROM telegram WHERE season_id = ?"
        ]
        assert 0 <= sql_type < 5, "索引长度错误"
        #logger.info(f'查询信息表中{target_id}的信息')
        
        try:
            cur.execute(sqls[sql_type], (target_id,))
        except Exception as e:
            ##logger.error(f'查询信息表时发生错误:\n{e}')
            raise BiliDatebaseError(f"数据库查询信息表时发生错误:{e.args[0]}")
        else:
            result = cur.fetchone()
            return result

    def query_all(self, sql_type: int) -> List[Tuple]:
        '''获得所有的up/主播/番剧以进行更新检查

        Args:
            sql_type (int): 0-up;1-主播;2-番剧;3-用户;4-群组

        Returns:
            List[Tuple]: 查询结果
        '''

        sqls = [
            "SELECT up_uid, up_name, latest_update FROM up",
            "SELECT liver_uid, liver_name, is_live, live_room FROM liver",
            "SELECT season_id, telegram_title, episode FROM telegram WHERE is_finish IS FALSE",
            "SELECT user_id FROM qq_user",
            "SELECT group_id FROM qq_group"
        ]
        
        assert 0 <= sql_type < 5, "索引长度错误"
        cur = self.conn.cursor()

        try:
            cur.execute(sqls[sql_type])
        except Exception as e:
            ##logger.error(f'查询信息表时发生错误:\n{e}')
            raise BiliDatebaseError(f"数据库查询信息表时发生错误:{e.args[0]}")

        else:
            result = cur.fetchall()
            return result

    def query_user_relation(self, sql_type: int, target_id: str) -> List[Tuple]:
        '''查询个人相关的关注

        Args:
            sql_type (int): 0-关注up的所有用户;1-用户关注的所有up;2-关注主播的所有用户;3-用户关注的所有主播;4-关注番剧的所有用户;5-用户关注的所有番剧
            target_id (str): 用户/up/主播/番剧的id

        Returns:
            List[Tuple]: 查询结果列表
        '''

        sqls = [
            "SELECT user_id FROM up_follower WHERE up_uid = ?",
            "SELECT up_uid FROM up_follower WHERE user_id = ?",
            "SELECT user_id FROM liver_follower WHERE liver_uid = ?",
            "SELECT liver_uid FROM liver_follower WHERE user_id = ?",
            "SELECT user_id FROM telegram_follower WHERE season_id = ?",
            "SELECT season_id FROM telegram_follower WHERE user_id = ?"
        ]
        assert 0 <= sql_type < 6, "索引长度错误"

        cur = self.conn.cursor()
        ##logger.info(f'查询个人关注')
        try:
            cur.execute(sqls[sql_type], (target_id, ))
        except Exception as e:
            ##logger.error(f'查询个人关注时发生错误:\n{e}')
            raise BiliDatebaseError(f"数据库查询个人关注时发生错误:{e.args[0]}")
        else:
            result = cur.fetchall()
            return result
    
    def query_group_relation(self, sql_type: int, target_id: str) -> List[Tuple]:
        '''查询群相关的关注

        Args:
            sql_type (int): 0-关注up的所有群;1-群关注的所有up;2-关注主播的所有群;3-群关注的所有主播;4-关注番剧的所有群;5-群关注的所有番剧
            target_id (str): 群/up/主播/番剧的id

        Returns:
            List[Tuple]: 查询结果
        '''

        sqls = [
            "SELECT group_id FROM up_follower WHERE up_uid = ?",
            "SELECT up_uid FROM up_follower WHERE group_id = ?",
            "SELECT group_id FROM liver_follower WHERE liver_uid = ?",
            "SELECT liver_uid FROM liver_follower WHERE group_id = ?",
            "SELECT group_id FROM telegram_follower WHERE season_id = ?",
            "SELECT season_id FROM telegram_follower WHERE group_id = ?"
        ]
        assert 0 <= sql_type < 6, "索引长度错误"

        cur = self.conn.cursor()
        ##logger.info(f'查询群组关注')
        try:
            cur.execute(sqls[sql_type], (target_id, ))
        except Exception as e:
            ##logger.error(f'查询群组关注时发生错误:\n{e}')
            raise BiliDatebaseError(f"数据库查询群组关注时发生错误:{e.args[0]}")
        else:
            result = cur.fetchall()
            return result

    def query_specified_realtion(self, sql_type: int, user_id: str, target_id: str) -> bool:
        '''查询一对一的关注

        Args:
            sql_type (int): 0 个人-up;1 群组-up;2 个人-主播;3 群组-主播;4 个人-番剧;5 群组-番剧
            user_id (str): 用户/群组id
            target_id (str): up/主播/番剧id

        Returns:
            bool: 是否关注
        '''

        sqls = [
            "SELECT user_id, up_uid FROM up_follower WHERE user_id = ? AND up_uid = ?",
            "SELECT group_id, up_uid FROM up_follower WHERE group_id = ? AND up_uid = ?",
            "SELECT user_id, liver_uid FROM liver_follower WHERE user_id = ? AND liver_uid = ?",
            "SELECT group_id, liver_uid FROM liver_follower WHERE group_id = ? AND liver_uid = ?",
            "SELECT user_id, season_id FROM telegram_follower WHERE user_id = ? AND season_id = ?",
            "SELECT group_id, season_id FROM telegram_follower WHERE group_id = ? AND season_id = ?",
        ]
        
        assert 0 <= sql_type < 6, "索引长度错误"
        
        cur = self.conn.cursor()
        ##logger.info(f'查询一对一关注')
        try:
            cur.execute(sqls[sql_type], (user_id, target_id))
        except Exception as e:
            ##logger.error(f'查询一对一关注时发生错误:\n{e}')
            raise BiliDatebaseError(f"数据库查询一对一关注时发生错误:{e.args[0]}")
        else:
            result = cur.fetchone()
            if result:
                return True
            else:
                return False


    def delete_relation(self, sql_type: int, user_id: str, uid: str) -> bool:
        '''进行取关操作

        Args:
            sql_type (int): 0-用户取关up;1-群取关up;2-用户取关主播;3-群取关主播;4-用户取关番剧;5-群取关番剧
            user_id (str): 用户/群id
            uid (str): up/主播/番剧id

        Returns:
            bool: 是否成功
        '''
        sqls = [
            "DELETE FROM up_follower WHERE user_id = ? AND up_uid = ?",
            "DELETE FROM up_follower WHERE group_id = ? AND up_uid = ?",
            "DELETE FROM liver_follower WHERE user_id = ? AND liver_uid = ?",
            "DELETE FROM liver_follower WHERE group_id = ? AND liver_uid = ?",
            "DELETE FROM telegram_follower WHERE user_id = ? AND season_id = ?",
            "DELETE FROM telegram_follower WHERE group_id = ? AND season_id = ?"
        ]
        assert 0 <= sql_type < 6, "索引长度错误"

        cur = self.conn.cursor()
        ##logger.info(f'进行取关操作,取消{user_id}与{uid}之间的关注关系')
        
        try:
            cur.execute(sqls[sql_type], (user_id, uid))
        except Exception as e:
            ##logger.error(f'取关时发生错误:\n{e}')
            raise BiliDatebaseError(f"数据库取关时发生错误:{e.args[0]}")

        else:
            ##logger.info(f'取关成功')
            self.conn.commit()
            return True
        
    def update_info(self, sql_type: int, *args) -> bool:
        '''更新up/主播/番剧信息

        Args:
            sql_type (int): 0-更新up;1-更新主播;2-更新番剧
            args     : up-整数时间戳,uid;主播-True/False, uid;番剧-整数集数, 是否完结, season_id

        Returns:
            bool: 是否成功
        '''

        sqls = [
            "UPDATE up SET latest_update = ? WHERE up_uid = ?",
            "UPDATE liver SET is_live = ? WHERE liver_uid = ?",
            "UPDATE telegram SET episode = ?, is_finish = ? WHERE season_id = ?"
        ]
        assert 0 <= sql_type < 3, "索引长度错误"

        cur = self.conn.cursor()
        ##logger.info(f'更新信息表')
        
        try:
            logger.debug(f"args = {args}")
            cur.execute(sqls[sql_type], args)
        except Exception as e:
            ##logger.debug(f'更新信息表时发生错误:\n{e}')
            raise e
        else:
            ##logger.info(f'更新信息表成功')
            self.conn.commit()
            return True

    def delete_info(self, sql_type: int, target_id: str) -> bool:
        '''删除用户/群组/up/主播/番剧信息

        Args:
            sql_type (int): 0-用户;1-群组;2-up;3-主播;4-番剧信息
            target_id (str): 用户/群组/up/主播/番剧id       

        Returns:
            bool: 是否成功
        '''

        sqls = [
            "DELETE FROM qq_user WHERE user_id = ?",
            "DELETE FROM qq_group WHERE group_id = ?",
            "DELETE FROM up WHERE up_uid = ?",
            "DELETE FROM liver WHERE liver_uid = ?",
            "DELETE FROM telegram WHERE season_id = ?"
        ]

        cur = self.conn.cursor()
        ##logger.info(f'从信息表中删除{target_id}的信息')
        
        try:
            cur.execute(sqls[sql_type], (target_id,))
        except Exception as e:
            ##logger.error(f'从信息表中删除时发生错误:\n{e}')
            raise BiliDatebaseError(f"数据库删除信息时发生错误:{e.args[0]}")

        else:
            ##logger.info(f'删除成功')
            self.conn.commit()
            return True
    
    def get_from_json(self) -> None:
        '''从json文件中读取数据,写入数据库
        '''
        dir_path = dirname(abspath(__file__)) + "/file/"

        if not os.path.exists(dir_path + "user"):
            return

        # 插入用户
        for json_file_name in os.listdir(dir_path + "user"):
            user_id = json_file_name.split(".")[0]
            with open(dir_path + "user/" + json_file_name, "r", encoding='utf-8') as f:
                user_info = json.load(f)
                user_name = user_info[0]

                self.insert_info(0, user_id, user_name)

                liver_list = user_info[1]
                for liver in liver_list:
                    liver_uid = liver.split()[1][:-1]
                    self.insert_relation(2, liver_uid, user_id)
                
                up_list = user_info[2]
                for up in up_list:
                    up_uid = up.split()[1][:-1]
                    self.insert_relation(0, up_uid, user_id)
                
                tele_list = user_info[3]
                for tele in tele_list:
                    tele_uid = tele.split()[1][:-1]
                    self.insert_relation(4, tele_uid, user_id)
            
            os.remove(dir_path + "user/" + json_file_name)
        os.rmdir(dir_path + "user/")
            # delete file
        
        # 插入群组
        for json_file_name in os.listdir(dir_path + "group"):
            group_id = json_file_name.split(".")[0]
            with open(dir_path + "group/" + json_file_name, "r", encoding='utf-8') as f:
                group_info = json.load(f)
                group_name = group_info[0]

                self.insert_info(1, group_id, group_name)

                liver_list = group_info[1]
                for liver in liver_list:
                    liver_uid = liver.split()[1][:-1]
                    self.insert_relation(3, liver_uid, group_id)
                
                up_list = group_info[2]
                for up in up_list:
                    up_uid = up.split()[1][:-1]
                    self.insert_relation(1, up_uid, group_id)
                
                tele_list = group_info[3]
                for tele in tele_list:
                    tele_uid = tele.split()[1][:-1]
                    self.insert_relation(5, tele_uid, group_id)  
            
            os.remove(dir_path + "group/" + json_file_name) 
        os.rmdir(dir_path + "group/")     
        # 插入up主
        for json_file_name in os.listdir(dir_path + "up"):
            up_uid = json_file_name.split(".")[0]
            with open(dir_path + "up/" + json_file_name, "r", encoding='utf-8') as f:
                up_info = json.load(f)
                up_name = up_info[0]
                up_timestamp = up_info[1]

                self.insert_info(2, up_uid, up_name, up_timestamp)
            
            os.remove(dir_path + "up/" + json_file_name)
        os.rmdir(dir_path + "up/")

        # 插入主播
        for json_file_name in os.listdir(dir_path + "stream"):
            liver_uid = json_file_name.split(".")[0]
            with open(dir_path + "stream/" + json_file_name, "r", encoding='utf-8') as f:
                liver_info = json.load(f)
                self.insert_info(3, liver_uid, liver_info[0], liver_info[1], liver_info[2])
            
            os.remove(dir_path + "stream/" + json_file_name)
        
        os.rmdir(dir_path + "stream/")
        # 插入番剧
        for json_file_name in os.listdir(dir_path + "telegram"):
            tele_uid = json_file_name.split(".")[0]
            with open(dir_path + "telegram/" + json_file_name, "r", encoding='utf-8') as f:
                tele_info = json.load(f)
                self.insert_info(4, tele_uid, tele_info[0], tele_info[1])
            
            os.remove(dir_path + "telegram/" + json_file_name)
        os.rmdir(dir_path + "telegram/")
        
bili_database = BiliDatabase()
#bili_database.get_from_json()