from cmath import exp
from .db import bili_database
from .exception import BiliConnectionError, BiliDatebaseError
import httpx
import json
from typing import Tuple, List
import sys
import traceback
import nonebot
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageSegment
from .basicFunc import *

__PLUGIN_NAME = "B站整合~视频"
BASEURL = 'https://api.bilibili.com/x/space/arc/search?mid={}&ps=30&tid=0&pn=1&keyword=&order=pubdate&jsonp=jsonp'
USERINFOURL = 'https://api.bilibili.com/x/space/acc/info?mid={}&jsonp=jsonp'
header = {
    'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv2.0.1) Gecko/20100101 Firefox/4.0.1'
}

# 视频
async def get_latest_video(uid: str, last_udpate_time: int) -> Tuple[bool, str, str, int, str]:
    """
    @description  :
    根据uid和时间戳, 返回元组，表示存在新视频或无新视频
    ---------
    @param  :
    uid: 查询新视频用户的uid
    last_udpate_time: 数据库中记录的最新视频的时间戳
    -------
    @Returns  :
    返回一个元组[是否更新，bv号，标题，发布时间戳，封面的链接]
    -------
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url = BASEURL.format(uid), headers=header)
    except Exception as e:
        raise BiliConnectionError(f"获取up主<{uid}>的视频列表时发生网络错误:{e.args[0]}")
    if response.status_code != 200:
        raise BiliConnectionError(f"获取视频列表时连接出错:状态码={response.status_code}")

    response = json.loads(response.text)
    #assert len(response['data']['list']['vlist']) != 0, '用户{}无发布视频'.format(uid)
    latest_video = response['data']['list']['vlist'][0] if len(response['data']['list']['vlist']) != 0 else 0
    post_time = int(latest_video['created']) if len(response['data']['list']['vlist']) else 0
    
    if post_time > last_udpate_time:
        # 发现新视频
        title = latest_video['title']
        bvID = latest_video['bvid']
        cover_url = latest_video['pic']
        return (True, bvID, title, post_time, cover_url)
    return (False, '', '', 0, '')

async def check_up_update() -> None:
    """
    @description  :
    检查关注UP主是否更新新视频，如果更新则通知用户并写入文件
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    try:
        up_list = bili_database.query_all(0)
        schedBot = nonebot.get_bot()
        #assert status == True, "数据库发生错误"
        for up_uid, up_name, latest_timestamp in up_list:
            res = await get_latest_video(up_uid, latest_timestamp)

            if res[0]:
                logger.info(f'{__PLUGIN_NAME}检测到up主<{up_name}>更新了视频')
                textMsg = f"【B站动态】\n <{up_name}> 更新了视频\n标题: {res[2]}\n链接: https://www.bilibili.com/video/{res[1]}"
                
                user_list = bili_database.query_user_relation(0, up_uid)
                for user_id in user_list:
                    await schedBot.send_msg(message=textMsg + MessageSegment.image(res[4]), user_id=user_id[0])
                
                group_list = bili_database.query_group_relation(0, up_uid)
                for group_id in group_list:
                    await schedBot.send_msg(message=textMsg + MessageSegment.image(res[4]), group_id=group_id[0])
                
                bili_database.update_info(0, up_uid, res[3])
    except Exception as _:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n检测up主<{up_name}>更新状况时发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())

async def init_up_info(uid: str) -> Tuple[str, int]:
    """
    @description  :
    根据uid查询up主信息
    ---------
    @param  :
    uid：用户的uid
    -------
    @Returns  :
    返回一个元组
    [up主名字，最新视频的时间戳]
    -------
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url=USERINFOURL.format(uid), headers=header)
    except Exception as e:
        raise BiliConnectionError(f"获取up主<{uid}>的信息时发生网络错误:{e.args[0]}")
    if response.status_code != 200:
        raise BiliConnectionError(f"获取up主<{uid}>的信息时连接出错:状态码={response.status_code}")
    
    response = json.loads(response.text)
    if response['code'] == 0:
        user_name = response['data']['name']
        res = await get_latest_video(uid, 0)
        return (user_name, res[3])
    else:
        return ('', '')

async def follow_up(uid: str, user_id: str, user_type: int) -> Tuple[bool, str]:
    '''根据用户或群关注up，修改数据库

    Args:
        uid (str): up的uid
        user_id (str): 用户的qq或群号
        user_type (int): 0-个人用户，1-群

    Returns:
        Tuple[bool, str]: [是否成功，信息]
    '''
    
    # 处理参数错误
    if not uid.isdigit():
        logger.error(f'{__PLUGIN_NAME}存在错误参数<{uid}>')
        return (False, uid + "(错误参数)")
    
    try:
        result = bili_database.query_info(2, uid)
        
        # up信息不存在于数据库,对数据库进行更新
        if not result:
            up_name, latest_timestamp = await init_up_info(uid)

            if up_name:
                bili_database.insert_info(2, uid, up_name, latest_timestamp)
                bili_database.insert_relation(0 + user_type, uid, user_id)
                logger.info(f"{__PLUGIN_NAME}用户/群 <{user_id}> 关注主播 <{up_name}> 成功")
                return (True, up_name + f"(uid: {uid})")
            else:
                logger.info(f'{__PLUGIN_NAME}up({uid})不存在，请检查uid')
                return (False, uid + "(uid错误)")
        # 处理已关注
        result1 = bili_database.query_specified_realtion(0 + user_type, user_id, uid)
        
        if result1:
            logger.info(f"{__PLUGIN_NAME}用户/群 <{user_id}> 已经关注了up <{result[1]}>")
            return (False, result[1] + "(已关注)")
    
        # 进行关注
        bili_database.insert_relation(0 + user_type, uid, user_id)
        logger.info(f"{__PLUGIN_NAME}用户/群 <{user_id}> 关注up <{result[1]}> 成功")
        return (True, result[1] + f"(uid: {uid})")
    except BiliConnectionError:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n获取up主 <{uid}> B站信息发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())
        return (False, uid + "(网络错误)")
    except BiliDatebaseError:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n关注up主 <{uid}>时数据库发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())
        return (False, uid + "(数据库错误)")
    except Exception:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n关注up主 <{uid}>时发生意料之外的错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())
        return (False, uid + "(未知错误,请查看日志)")

async def unfollow_up(uid: str, user_id: str, user_type: int) -> Tuple[bool, str]:
    '''根据个人用户或群取关up主，修改up文件

    Args:
        uid (str): up的uid
        user_id (str): 用户的qq号/群号
        user_type (int): 0-个人用户，1-群

    Returns:
        Tuple[bool, str]: [是否成功，信息]
    '''
    
    # 处理参数错误
    if not uid.isdigit():
        logger.error(f'{__PLUGIN_NAME}存在错误参数 <{uid}>')
        return (False, uid + "(错误参数)")
    try:
    # 处理未关注
        result = bili_database.query_specified_realtion(0 + user_type, user_id, uid)
        if not result:
            logger.info(f'{__PLUGIN_NAME}用户/群 <{user_id}> 未关注up <{uid}>')
            return (False, uid + "(未关注)")
        
        # 进行取关
        bili_database.delete_relation(0 + user_type, user_id, uid)
        logger.info(f'{__PLUGIN_NAME}用户/群 <{user_id}> 取关up <{uid}> 成功')

        return (True, bili_database.query_info(2, uid)[1]  + f"(uid: {uid})") 
    except BiliDatebaseError:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n取关up主 <{uid}> 时数据库发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())
        return (False, uid + "(数据库错误)")

async def follow_up_list(
    user_id: int, 
    uidList: List[str], 
    user_type: int
    ) -> List[List[str]]:
    '''个人用户/群关注up主

    Args:
        user_id (int): qq号/群号
        uidList (List[str]): up主的uid
        user_type (int): 0-个人用户，1-群        

    Returns:
        List[List[str]]: [是否成功，信息]
    '''
    successList = []
    failList = []

    for uid in uidList:
        isSuccess, s = await follow_up(uid, str(user_id), user_type)
        if isSuccess:
            successList.append(s)
        else:
            failList.append(s)

    return [successList, failList]

async def unfollow_up_list(
    user_id: int, 
    uidList: List[str],
    user_type: int
    ) -> List[List[str]]:
    '''个人用户/群取关up主

    Args:
        user_id (int): qq号/群号
        uidList (List[str]): 取关的up主
        user_type (int): 0-个人用户，1-群

    Returns:
        List[List[str]]: [是否成功，信息]
    '''
    successList = []
    failList = []

    for uid in uidList:
        isSuccess, s = await unfollow_up(uid, user_id, user_type)
        if isSuccess:
            successList.append(s)
        else:
            failList.append(s)
    
    return [successList, failList]