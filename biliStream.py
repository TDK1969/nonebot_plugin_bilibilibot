import json
from typing import Tuple, List
import sys
import traceback
import nonebot
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from .basicFunc import *
from .db import bili_database
from .exception import *
from random import choice
import asyncio
from .bili_client import bili_client

__PLUGIN_NAME = "[bilibilibot~直播]"
BASEURL = 'https://api.bilibili.com/x/space/arc/search?mid={}&ps=30&tid=0&pn=1&keyword=&order=pubdate&jsonp=jsonp'
USERINFOURL = 'https://api.bilibili.com/x/space/acc/info?mid={}&jsonp=jsonp'
LIVEINFOURL = 'https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo?room_id={}&protocol=0,1&format=0,1,2&codec=0,1&qn=0&platform=web&ptype=8'

async def check_bili_live() -> None:
    """
    @description  :
    检查数据库中所有主播的开播状态
    如果关注的主播开播，则通知所有关注的用户
    如果主播开播状态改变,则更新数据库
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    liver_list = bili_database.query_all(1)
    logger.debug(f'{__PLUGIN_NAME}主播数据库:{liver_list}')
    sched_bot = nonebot.get_bot()
    
    results = await asyncio.gather(
        *[bili_client.get_live_status(liver_info[0], liver_info[3]) for liver_info in liver_list],
        return_exceptions=True
    )
    logger.debug(f'{__PLUGIN_NAME}直播状态结果:{results}')
    
    for i in range(len(liver_list)):
        if isinstance(results[i], tuple):
            if results[i][0] and not liver_list[i][2]:
                logger.info(f'[{__PLUGIN_NAME}]检测到主播 <{liver_list[i][1]}> 已开播！')
                text_msg = '【直播动态】\n<{}>正在直播!\n标题: {}\n链接: {}'.format(liver_list[i][1], results[i][1], f"https://live.bilibili.com/{liver_list[i][3]}")
                
                logger.info(f'[{__PLUGIN_NAME}]向粉丝发送开播通知')
                bili_database.update_info(1, 1, liver_list[i][0])

                user_list = bili_database.query_user_relation(2, liver_list[i][0])
                for user in user_list:
                    await sched_bot.send_msg(message=text_msg + MessageSegment.image(results[i][2]), user_id=user[0])
                
                group_list = bili_database.query_group_relation(2, liver_list[i][0])
                for group in group_list:
                    await sched_bot.send_msg(message=text_msg + MessageSegment.image(results[i][2]), group_id=group[0])
            elif not results[i][0] and liver_list[i][2]:
                logger.info(f"[{__PLUGIN_NAME}]检测到主播 <{liver_list[i][1]}> 已下播")
                bili_database.update_info(1, 0, liver_list[i][0])
        elif isinstance(results[i], (BiliAPIRetCodeError, BiliStatusCodeError, BiliConnectionError)):
            exception_msg = f'[错误报告]\n检测主播 <{liver_list[i][1]}> 开播情况时发生错误\n错误类型: {type(results[i])}\n错误信息: {results[i]}'
            logger.error(f"[{__PLUGIN_NAME}]" + exception_msg)
    
async def follow_liver(uid: str, user_id: str, user_type: int) -> Tuple[bool, str]:
    '''根据用户/群关注主播，修改数据库

    Args:
        uid (str): 主播的uid
        user_id (str): 用户的uid或群号
        user_type (int): 0-用户，1-群

    Returns:
        Tuple[bool, str]: [是否成功，主播名(uid) | 主播uid(失败原因)]
    '''
    
    if not uid.isdigit():
        logger.error(f'{__PLUGIN_NAME}存在错误参数 <{uid}>')
        return (False, uid + "(错误参数)")
    uid = str(int(uid))
    try:
        result = bili_database.query_info(3, uid)
        
        if not result:
            # 主播在数据库中无信息,进行数据库更新
            liver_name, room_url = await bili_client.init_liver_info(uid)
        
            if liver_name and room_url:
                bili_database.insert_info(3, uid, liver_name, False, room_url)
                bili_database.insert_relation(2 + user_type, uid, user_id)
                logger.info(f"{__PLUGIN_NAME}用户/群 <{user_id}> 关注主播 <{liver_name}> 成功")
                return (True, liver_name + f"(uid: {uid})")
            elif liver_name:
                logger.debug(f'{__PLUGIN_NAME}主播 <{liver_name}>未开通直播间')
                return (False, uid + "(该用户未开通直播间)")
            else:
                logger.debug(f'{__PLUGIN_NAME}主播 <{uid}> 不存在')
                return (False, uid + "(非法uid)")
        
        if bili_database.query_specified_realtion(2 + user_type, user_id, uid):
            logger.debug(f'{__PLUGIN_NAME}主播 <{result[1]}> 已关注')
            return (False, uid + "(已关注)")
   
        bili_database.insert_relation(2 + user_type, uid, user_id)
        logger.info(f"{__PLUGIN_NAME}用户/群 <{user_id}> 关注主播 <{result[1]}> 成功")
        return (True, result[1] + f"(uid: {uid})")
    except (BiliConnectionError, BiliAPIRetCodeError, BiliStatusCodeError):
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n获取主播 <{uid}> B站信息发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())
        return (False, uid + "(网络错误)")
    except BiliNoLiveRoom:
        return (False, uid + "(未开通直播间)")
    except BiliDatebaseError:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n关注主播 <{uid}> 时数据库发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())
        return (False, uid + "(数据库错误)")
    except Exception:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n关注主播 <{uid}> 时发生意料之外的错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())
        return (False, uid + "(未知错误,请查看日志)")

async def unfollower_liver(uid: str, user_id: str, user_type: int) -> Tuple[bool, str]:
    '''根据用户取关主播，修改主播文件

    Args:
        uid (str): 主播的uid
        user_id (int):QQ号/群号
        user_type (int): 0-个人用户，1-群

    Returns:
        Tuple[bool, str]: [是否成功，主播名 | 失败原因]
    '''
    if not uid.isdigit():
        logger.error(f'{__PLUGIN_NAME}存在错误参数 <{uid}>')
        return (False, uid + "(错误参数)")
    try:
        result = bili_database.query_specified_realtion(2 + user_type, user_id, uid)
        if result:
            liver_info = bili_database.query_info(3, uid)
            bili_database.delete_relation(2 + user_type, user_id, uid)
            # 如果没人关注,删除主播
            return (True, liver_info[1] + f"(uid: {uid})")
        else:
            logger.debug(f'{__PLUGIN_NAME}用户 <{user_id}> 未关注主播<{uid}>')
            return (False, uid + "(未关注)")
    except BiliDatebaseError:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n取关主播 <{uid}> 时数据库发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())
        return (False, uid + "(数据库错误)")

async def follow_liver_list(
    user_id: int, 
    uid_list: List[str],
    user_type: int
    ) -> List[List[str]]:
    '''用户/群对主播进行关注

    Args:
        user_id (int): 用户qq或群号
        uid_list (List[str]): 关注的主播uid
        user_type (int): 0-用户, 1-群

    Returns:
        List[List[str]]: [[关注成功], [关注失败]]
    '''

    success_list = []
    fail_list = []

    for uid in uid_list:
        isSuccess, s = await follow_liver(uid, str(user_id), user_type)
        if isSuccess:
            success_list.append(s)
        else:
            fail_list.append(s)

    return [success_list, fail_list]


async def unfollow_liver_list(
    user_id: int, 
    uid_list: List[str],
    user_type: int
    ) -> List[List[str]]:
    '''用户/群对主播取关

    Args:
        user_id (int): 用户qq/群号
        uid_list (List[str]): 取关主播列表
        user_type (int): 0-用户, 1-群

    Returns:
        List[List[str]]: [成功列表，失败列表]
    '''

    success_list = []
    fail_list = []

    for uid in uid_list:
        isSuccess, s = await unfollower_liver(uid, str(user_id), user_type)
        if isSuccess:
            success_list.append(s)
        else:
            fail_list.append(s)
    
    return [success_list, fail_list]