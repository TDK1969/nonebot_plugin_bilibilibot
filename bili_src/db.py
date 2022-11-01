import sqlite3
from typing import List, Tuple
from nonebot.log import logger
from os.path import abspath, dirname
from .exception import *

class BiliDatabase():
    def __init__(self) -> None:
        self.db_name = dirname(abspath(__file__)) + "/../bilibili_2.db"
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
        
        #创建动态表   
        cur.execute('''CREATE TABLE IF NOT EXISTS dynamic
            (
                uid VARCHAR(20) PRIMARY KEY NOT NULL,
                u_name VARCHAR(50) NOT NULL,
                pin_id_str VARCHAR(25) NOT NULL,
                latest_timestamp INT NOT NULL
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
        
        # 创建关注动态表
        cur.execute('''CREATE TABLE IF NOT EXISTS dynamic_follower
            (
                id INTERGER PRIMARY KEY,
                uid VARCHAR(20) NOT NULL,
                user_id VARCHAR(20),
                group_id VARCHAR(20)
            )
            ''')

        logger.debug(f'数据库初始化完毕')
        
        cur.close()
        self.conn.commit()

    def insert_info(self, sql_type: int, *args) -> bool:
        '''插入信息表的通用操作

        Args:
            type (int): 0-用户;1-群组;2-up;3-主播;4-番剧;5-动态
            args: 
                0-用户:   user_id, user_name
                1-群组:   group_id, group_name
                2-up主:   up_uid, up_name, latest_update
                3-主播:   liver_uid, liver_name, is_live, live_room
                4-番剧:   season_id, telegram_title, episode, is_finish
                5-动态:   uid, u_name, pin_id_str, latest_timestamp

        Returns:
            bool: 是否成功
        '''
        cur = self.conn.cursor()

        sqls = [
            "INSERT INTO qq_user(user_id, user_name) VALUES (?, ?)",
            "INSERT INTO qq_group(group_id, group_name) VALUES (?, ?)",
            "INSERT INTO up(up_uid, up_name, latest_update) VALUES (?, ?, ?)",
            "INSERT INTO liver(liver_uid, liver_name, is_live, live_room) VALUES (?, ?, ?, ?)",
            "INSERT INTO telegram(season_id, telegram_title, episode, is_finish) VALUES (?, ?, ?, ?)",
            "INSERT INTO dynamic(uid, u_name, pin_id_str, latest_timestamp) VALUES (?, ?, ?, ?)"
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
            type (int): 0-个人关注up;1-群关注up;2-个人关注主播;3-群关注主播;4-个人关注番剧;5-群关注番剧;6-个人关注动态;7-群关注动态
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
            "INSERT INTO dynamic_follower(id, uid, user_id) VALUES (NULL, ?, ?)",
            "INSERT INTO dynamic_follower(id, uid, group_id) VALUES (NULL, ?, ?)"
        ]
        cur = self.conn.cursor()
        
        assert 0 <= sql_type < len(sqls), "索引长度错误"
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
            sql_type (int): 0-用户;1-群组;2-up;3-主播;4-番剧;5-动态
            target_id (str): up/主播/番剧/用户/群/动态发布者的id

        Returns:
            Tuple: 查询结果
        '''
        cur = self.conn.cursor()
        sqls = [
            "SELECT user_id, user_name FROM qq_user WHERE user_id = ?",
            "SELECT group_id, group_name FROM qq_group WHERE group_id = ?",
            "SELECT up_uid, up_name, latest_update FROM up WHERE up_uid = ?",
            "SELECT liver_uid, liver_name, is_live, live_room FROM liver WHERE liver_uid = ?",
            "SELECT season_id, telegram_title, episode FROM telegram WHERE season_id = ?",
            "SELECT uid, u_name, pin_id_str, latest_timestamp FROM dynamic WHERE uid = ?"
        ]
        assert 0 <= sql_type < len(sqls), "索引长度错误"
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
            sql_type (int): 0-up;1-主播;2-番剧;3-用户;4-群组;5-动态

        Returns:
            List[Tuple]: 查询结果
        '''

        sqls = [
            "SELECT up_uid, up_name, latest_update FROM up",
            "SELECT liver_uid, liver_name, is_live, live_room FROM liver",
            "SELECT season_id, telegram_title, episode FROM telegram WHERE is_finish = 0",
            "SELECT user_id FROM qq_user",
            "SELECT group_id FROM qq_group",
            "SELECT uid, u_name, pin_id_str, latest_timestamp FROM dynamic"
        ]
        
        assert 0 <= sql_type < len(sqls), "索引长度错误"
        cur = self.conn.cursor()

        try:
            cur.execute(sqls[sql_type])
        except Exception as e:
            ##logger.error(f'查询信息表时发生错误:\n{e}')
            raise BiliDatebaseError(f"数据库查询信息表时发生错误:{e.args[0]}")

        else:
            result = cur.fetchall()
            return result

    def query_user_relation(self, sql_type: int, target_id: str) -> List[str]:
        '''查询个人相关的关注

        Args:
            sql_type (int): 
            0-关注up的所有用户;1-用户关注的所有up;
            2-关注主播的所有用户;3-用户关注的所有主播;
            4-关注番剧的所有用户;5-用户关注的所有番剧;
            6-关注动态主的所有用户;7-用户关注的所有动态主
            target_id (str): 用户/up/主播/番剧/动态主的id

        Returns:
            List[str]: 查询结果列表
        '''

        sqls = [
            "SELECT user_id FROM up_follower WHERE up_uid = ?",
            "SELECT up_uid FROM up_follower WHERE user_id = ?",
            "SELECT user_id FROM liver_follower WHERE liver_uid = ?",
            "SELECT liver_uid FROM liver_follower WHERE user_id = ?",
            "SELECT user_id FROM telegram_follower WHERE season_id = ?",
            "SELECT season_id FROM telegram_follower WHERE user_id = ?",
            "SELECT user_id FROM dynamic_follower WHERE uid = ?",
            "SELECT uid FROM dynamic_follower WHERE user_id = ?"
        ]
        assert 0 <= sql_type < len(sqls), "索引长度错误"

        cur = self.conn.cursor()
        ##logger.info(f'查询个人关注')
        try:
            cur.execute(sqls[sql_type], (target_id, ))
        except Exception as e:
            ##logger.error(f'查询个人关注时发生错误:\n{e}')
            raise BiliDatebaseError(f"数据库查询个人关注时发生错误:{e.args[0]}")
        else:
            temp = cur.fetchall()
            if not temp:
                return []
            else:
                result = [i[0] for i in temp if i[0] is not None]
                return result
    
    def query_group_relation(self, sql_type: int, target_id: str) -> List[Tuple]:
        '''查询群相关的关注

        Args:
            sql_type (int): 
            0-关注up的所有群;1-群关注的所有up;
            2-关注主播的所有群;3-群关注的所有主播;
            4-关注番剧的所有群;5-群关注的所有番剧;
            6-关注动态主的所有群;7-群关注的所有动态主
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
            "SELECT season_id FROM telegram_follower WHERE group_id = ?",
            "SELECT group_id FROM dynamic_follower WHERE uid = ?",
            "SELECT uid FROM dynamic_follower WHERE group_id = ?"
        ]
        assert 0 <= sql_type < len(sqls), "索引长度错误"

        cur = self.conn.cursor()
        ##logger.info(f'查询群组关注')
        try:
            cur.execute(sqls[sql_type], (target_id, ))
        except Exception as e:
            ##logger.error(f'查询群组关注时发生错误:\n{e}')
            raise BiliDatebaseError(f"数据库查询群组关注时发生错误:{e.args[0]}")
        else:
            temp = cur.fetchall()
            if not temp:
                return []
            else:
                result = [i[0] for i in temp if i[0] is not None]
                return result

    def query_specified_realtion(self, sql_type: int, user_id: str, target_id: str) -> bool:
        '''查询一对一的关注

        Args:
            sql_type (int): 0 个人-up;1 群组-up;2 个人-主播;3 群组-主播;4 个人-番剧;5 群组-番剧;6 个人-动态;7 群组-动态
            user_id (str): 用户/群组id
            target_id (str): up/主播/番剧/动态主id

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
            "SELECT user_id, uid FROM dynamic_follower WHERE user_id = ? AND uid = ?",
            "SELECT group_id, uid FROM dynamic_follower WHERE group_id = ? AND uid = ?"
        ]
        
        assert 0 <= sql_type < len(sqls), "索引长度错误"
        
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
            sql_type (int): 
            0-用户取关up;1-群取关up;
            2-用户取关主播;3-群取关主播;
            4-用户取关番剧;5-群取关番剧;
            6-用户取关动态;7-群取关动态;
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
            "DELETE FROM telegram_follower WHERE group_id = ? AND season_id = ?",
            "DELETE FROM dynamic_follower WHERE user_id = ? AND uid = ?",
            "DELETE FROM dynamic_follower WHERE group_id = ? AND uid = ?"
        ]
        assert 0 <= sql_type < len(sqls), "索引长度错误"

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
            args     : 
            0 up-整数时间戳,uid;
            1 主播-True/False, uid;
            2 番剧-整数集数, 是否完结, season_id;
            3 动态-置顶动态id, uid;
            4 动态-最新动态时间戳, uid;

        Returns:
            bool: 是否成功
        '''

        sqls = [
            "UPDATE up SET latest_update = ? WHERE up_uid = ?",
            "UPDATE liver SET is_live = ? WHERE liver_uid = ?",
            "UPDATE telegram SET episode = ?, is_finish = ? WHERE season_id = ?",
            "UPDATE dynamic SET pin_id_str = ? WHERE uid = ?",
            "UPDATE dynamic SET latest_timestamp = ? WHERE uid = ?"
        ]
        assert 0 <= sql_type < len(sqls), "索引长度错误"

        cur = self.conn.cursor()
        ##logger.info(f'更新信息表')
        
        try:
            cur.execute(sqls[sql_type], args)
        except Exception as e:
            ##logger.debug(f'更新信息表时发生错误:\n{e}')
            raise e
        else:
            ##logger.info(f'更新信息表成功')
            self.conn.commit()
            return True

    def delete_info(self, sql_type: int, target_id: str) -> bool:
        '''删除用户/群组/up/主播/番剧/动态主信息

        Args:
            sql_type (int): 0-用户;1-群组;2-up;3-主播;4-番剧;5-动态主信息
            target_id (str): 用户/群组/up/主播/番剧/动态主id       

        Returns:
            bool: 是否成功
        '''

        sqls = [
            "DELETE FROM qq_user WHERE user_id = ?",
            "DELETE FROM qq_group WHERE group_id = ?",
            "DELETE FROM up WHERE up_uid = ?",
            "DELETE FROM liver WHERE liver_uid = ?",
            "DELETE FROM telegram WHERE season_id = ?",
            "DELETE FROM dynamic WHERE uid = ?"
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

    def check_dynamic_init(self) -> bool:
        '''检查是否完成动态初始化

        Returns:
            bool: 是否完成
        '''
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT is_dynamic_init FROM bili_sys")
        except Exception as e:
            raise BiliDatebaseError(f"数据库查询是否完成动态初始化时发生错误:{e.args[0]}")
        else:
            result = cur.fetchone()
            if result:
                return True
            else:
                cur.execute("UPDATE bili_sys SET is_dynamic_init = 1")
                self.conn.commit()
                return False
        
bili_database = BiliDatabase()