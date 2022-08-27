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

__PLUGIN_NAME = "B站整合~直播"
BASEURL = 'https://api.bilibili.com/x/space/arc/search?mid={}&ps=30&tid=0&pn=1&keyword=&order=pubdate&jsonp=jsonp'
USERINFOURL = 'https://api.bilibili.com/x/space/acc/info?mid={}&jsonp=jsonp'
LIVEINFOURL = 'https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo?room_id={}&protocol=0,1&format=0,1,2&codec=0,1&qn=0&platform=web&ptype=8'
header = {
    'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv2.0.1) Gecko/20100101 Firefox/4.0.1'
}

async def get_bili_live(uid: str) -> Tuple[bool, str, str]:
    """
    @description  :
    获取bilibili直播间信息
    ---------
    @param  :
    uid: 主播的uid，不是直播间号码
    -------
    @Returns  :
    返回一个元组
    [是否正在直播，直播间标题，直播间封面链接]
    -------
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url=USERINFOURL.format(uid), headers=header)
    except Exception as e:
        raise BiliConnectionError(f"获取主播<{uid}>的直播间信息时发生网络错误:{e.args[0]}")
    if response.status_code != 200:
        raise BiliConnectionError(f"获取主播<{uid}>的直播间信息时连接出错:状态码={response.status_code}")
    
    response = response.json()
    
    if response['code'] == 0:
        live_room = response['data']['live_room']
        if live_room is None:
            return (False, '', '')
        
        live_status = live_room['liveStatus']
        title = live_room['title']
        cover_url = live_room['cover']

        if live_status == 1:
            return (True, title, cover_url)
    return (False, '', '')

async def check_bili_live():
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
    try:
        liver_list = bili_database.query_all(1)
        sched_bot = nonebot.get_bot()
        
        for uid, liver_name, is_live, live_room in liver_list:
                is_living, title, cover_url = await get_bili_live(uid)
                if is_living and not is_live:
                    logger.info(f'[{__PLUGIN_NAME}]检测到主播 <{liver_name}> 已开播！')
                    text_msg = '【直播动态】\n<{}>正在直播!\n标题: {}\n链接: {}'.format(liver_name, title, live_room)
                    
                    logger.info(f'[{__PLUGIN_NAME}]向粉丝发送开播通知')
                    
                    user_list = bili_database.query_user_relation(2, uid)
                    for user in user_list:
                        await sched_bot.send_msg(message=text_msg + MessageSegment.image(cover_url), user_id=user[0])
                    
                    group_list = bili_database.query_group_relation(2, uid)
                    for group in group_list:
                        await sched_bot.send_msg(message=text_msg + MessageSegment.image(cover_url), group_id=group[0])
                    
                    bili_database.update_info(1, uid, True)
                elif not is_living and is_live:
                    logger.info(f"[{__PLUGIN_NAME}]检测到主播 <{liver_name}> 已下播")
                    bili_database.update_info(1, uid, False)
    except Exception as _:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n检测主播 <{liver_name}> 更新状况时发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())

async def init_liver_info(uid: str) -> Tuple[str, str]:
    """
    @description  :
    根据uid，返回直播间信息
    ---------
    @param  :
    uid： 用户的uid
    -------
    @Returns  :
    返回一个元组
    [用户名，直播间链接]
    -------
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url=USERINFOURL.format(uid), headers=header)
    except Exception as e:
        raise BiliConnectionError(f"获取主播<{uid}>的信息时发生网络错误:{e.args[0]}")
    if response.status_code != 200:
        raise BiliConnectionError(f"获取主播<{uid}>的信息时连接出错:状态码={response.status_code}")
    
    response = json.loads(response.text)
    if response['code'] == 0:
        user_name = response['data']['name']
        if response['data']["live_room"]:
            room_url = response['data']['live_room']['url']
        else:
            room_url = ""
        logger.info(f"[{__PLUGIN_NAME}]获取到uid为 <{uid}> 的用户名为 <{user_name}> , 直播间链接为 <{room_url}>")
        return (user_name, room_url)
    else:
        return ('', '')

async def get_uid_by_room_number(room_number: str) -> Tuple[bool, str]:
    """
    @description  :
    根据直播间号获得uid
    ---------
    @param  :
    room_number: 房间号
    -------
    @Returns  :
    返回一个元组
    [isSuccess, uid | '']
    -------
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url=LIVEINFOURL.format(room_number), headers=header)
    except Exception as e:
        raise BiliConnectionError(f"获取主播 <{uid}> 的房间信息时发生网络错误:{e.args[0]}")
    if response.status_code != 200:
        raise BiliConnectionError(f"获取主播 <{uid}> 的房间信息时连接出错:状态码={response.status_code}")
    response = json.loads(response.text)
    if response['code'] == 0:
        uid = response['data']['uid']
        return (True, str(uid))
    else:
        return (False, '')
    
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
    try:
        result = bili_database.query_info(3, uid)
        
        if not result:
            # 主播在数据库中无信息,进行数据库更新
            liver_name, room_url = await init_liver_info(uid)
        
            # TODO: 重复关注
            if liver_name and room_url:
                bili_database.insert_info(3, uid, liver_name, False, room_url)
                bili_database.insert_relation(2 + user_type, uid, user_id)
                logger.debug(f"{__PLUGIN_NAME}用户/群 <{user_id}> 关注主播 <{liver_name}> 成功")
                return (True, liver_name + f"(uid: {uid})")
            elif liver_name:
                logger.debug(f'{__PLUGIN_NAME}主播 <{liver_name}>未开通直播间')
                return (False, uid + "(该用户未开通直播间)")
            else:
                logger.debug(f'{__PLUGIN_NAME}主播 <{uid}> 不存在')
                return (False, uid + "(非法uid)")
        
        if bili_database.query_specified_realtion(2 + user_type, user_id, uid):
            logger.debug(f'{__PLUGIN_NAME}主播 <{uid}> 重复关注')
            return (False, uid + "(重复关注)")
   
        bili_database.insert_relation(2 + user_type, uid, user_id)
        logger.info(f"{__PLUGIN_NAME}用户/群 <{user_id}> 关注主播 <{result[1]}> 成功")
        return (True, result[1] + f"(uid: {uid})")
    except BiliConnectionError:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n获取主播 <{uid}> B站信息发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())
        return (False, uid + "(网络错误)")
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