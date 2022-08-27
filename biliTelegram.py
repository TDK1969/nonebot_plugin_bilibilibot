import json
from typing import Tuple, List, Union
import sys
import os
import traceback
import nonebot
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from .basicFunc import *
from .exception import *
import httpx
from .db import bili_database

__PLUGIN_NAME = "B站整合~影视/番剧"
biliTeleInfoUrl = 'https://api.bilibili.com/pgc/web/season/section?season_id={}'
GETSEASONIDAPI = 'https://api.bilibili.com/pgc/view/web/season?ep_id={}'
GETEPISODESAPI = 'https://api.bilibili.com/pgc/web/season/section?season_id={}'

header = {
    'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv2.0.1) Gecko/20100101 Firefox/4.0.1'
}

async def get_telegram_info(season_id: str, index: int) -> Tuple[bool, int, str, str, str]:
    """
    @description  :
    获取影视区作品的更新情况
    ---------
    @param  :
    season_id: 影视区作品的id
    index: 文件记录中的最新一集
    -------
    @Returns  :
    返回一个元组
    (是否更新, 最新集数, 最新集标题, 最新集链接, 封面链接)
    -------
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url=GETEPISODESAPI.format(season_id), headers=header)
    except Exception as e:
        raise BiliConnectionError(f"获取番剧<{season_id}>更新时发生网络错误:{e.args[0]}")
    if response.status_code != 200:
        raise BiliConnectionError(f"获取番剧<{season_id}>更新时连接出错:状态码={response.status_code}")

    response = json.loads(response.text)

    if response['code'] == 0:
        episodes = response['result']['main_section']['episodes']
        if len(episodes) > index:
            # 影视有更新
            latest_episode = episodes[-1]
            cover_url = latest_episode['cover']
            title = latest_episode['long_title']
            play_url = latest_episode['share_url']
            return (True, len(episodes), title, play_url, cover_url)
        else:
            return (False, 0, '', '', '')
    else:
        logger.debug(f"[{__PLUGIN_NAME}]查询的影视片不存在")
        return (False, 0, '', '', '')

async def get_seasonid_by_epid(ep_id: str) -> Tuple[bool, str, str, int]:
    """
    @description  :
    根据单集的epid，获取整季的seasonID以及名字
    ---------
    @param  :
    epid: 单集的epid
    -------
    @Returns  :
    返回一个元组
    [isSuccess, season_id, season_title, latest_index]
    
    -------
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url=GETSEASONIDAPI.format(ep_id), headers=header)
    except Exception as e:
        raise BiliConnectionError(f"获取番剧<{season_id}>信息时发生网络错误:{e.args[0]}")
    if response.status_code != 200:
        raise BiliConnectionError(f"获取番剧{season_id}信息时连接出错:状态码={response.status_code}")
    
    response = json.loads(response.text)
    if response['code'] == 0:
        season_id = str(response['result']['season_id'])
        season_title = response['result']['season_title']
        latest_index = len(response['result']['episodes'])

        return (True, season_id, season_title, latest_index)
    else:
        logger.debug(f'[{__PLUGIN_NAME}]获取seasonID失效，请检查epid')
        return (False, '', '', 0)

    
async def check_telegram_update():
    """
    @description  :
    检查数据库中的每一个影视节目是否更新，如果更新则向用户发送通知，并且更新文件
    ---------
    @param  :
    无
    -------
    @Returns  :
    无
    -------
    """
    try:
        telegram_list = bili_database.query_all(2)
        
        sched_bot = nonebot.get_bot()
        for season_id, telegram_title, episode in telegram_list:
            res = await get_telegram_info(season_id, episode)
            if res[0]:
                logger.info(f'[{__PLUGIN_NAME}]检测到影视剧 <{telegram_title}> 更新')
                bili_database.update_info(2, res[1], season_id)

                text_msg = "【B站动态】\n《{}》已更新第{}集\n标题: {}\n链接: {}\n".format(
                            telegram_title, res[1], res[2], res[3]
                        )
                cover_msg = MessageSegment.image(res[4])
                reported_msg = text_msg + cover_msg
                logger.info(f'[{__PLUGIN_NAME}]向关注用户发送更新通知')
                
                user_list = bili_database.query_user_relation(4, season_id)
                for user in user_list:
                    await sched_bot.send_msg(message=reported_msg, user_id=user[0])

                group_list = bili_database.query_group_relation(4, season_id)
                for group in group_list:
                    await sched_bot.send_msg(message=reported_msg, group_id=group[0])
                bili_database.update_info(2, season_id, res[1])
    except Exception as _:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n检测番剧{telegram_title}更新情况时发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"[{__PLUGIN_NAME}]" + exception_msg + traceback.format_exc())

async def follow_telegram(ep_id: str, user_id: str, user_type: int) -> Tuple[bool, str]:
    '''根据用户关注节目，修改节目的文件

    Args:
        ep_id (str): 节目的id
        user_id (str): 用户的qq号/群号
        user_type (int): 0-个人用户，1-群号

    Returns:
        Tuple[bool, str]: [是否成功，信息]
    '''

    if not ep_id.isdigit():
        logger.debug(f'[{__PLUGIN_NAME}]存在错误参数 <{ep_id}>')
        return (False, ep_id + "(错误参数)")
    try:
        res = await get_seasonid_by_epid(ep_id)
        if res[0]:
            _, season_id, telegram_title, episode = res
            telegram_info = bili_database.query_info(4, season_id)

            # 如果数据库无番剧信息,则插入番剧信息
            if not telegram_info:
                bili_database.insert_info(4, season_id, telegram_title, episode)

            result1 = bili_database.query_specified_realtion(4 + user_type, user_id, season_id)
            if result1:
                logger.debug(f'[{__PLUGIN_NAME}]用户 <{user_id}> 已关注节目 <{telegram_title}>')
                return (False, res[2] + "(已关注)")
            
            bili_database.insert_relation(4 + user_type, season_id, user_id)
            logger.info(f"[{__PLUGIN_NAME}]用户/群 <{user_id}> 关注番剧 <{telegram_title}> 成功")
            return (True, telegram_title + f"(season_id: {season_id})")
    
        else:
            return (False, ep_id + "(错误的epID)")
    except BiliConnectionError:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n获取番剧 <{ep_id}> 信息发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"[{__PLUGIN_NAME}]" + exception_msg + traceback.format_exc())
        return (False, ep_id + "(网络错误)")
    except BiliDatebaseError:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n关注番剧 <{season_id}> 时数据库发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"[{__PLUGIN_NAME}]" + exception_msg + traceback.format_exc())
        return (False, season_id + "(数据库错误)")
    except Exception:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n关注番剧 <{ep_id}> 时发生意料之外的错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"[{__PLUGIN_NAME}]" + exception_msg + traceback.format_exc())
        return (False, ep_id + "(未知错误,请查看日志)")
        
async def unfollow_telegram(season_id: str, user_id: str, user_type: int) -> Tuple[bool, str]:
    '''根据用户/群取关节目，修改节目文件

    Args:
        season_id (str): 节目的ID
        user_id (str): 用户qq号/群号
        user_type (int): 0-个人用户，1-群号

    Returns:
        Tuple[bool, str]: [是否成功, 信息]
    '''

    if not season_id.isdigit():
        return (False, season_id + "(错误参数)")
    
    try:
        result = bili_database.query_specified_realtion(4 + user_type, user_id, season_id)
        
        # 处理未关注
        if not result:
            logger.info(f'[{__PLUGIN_NAME}]用户/群 <{user_id}> 未关注番剧 <{season_id}>')
            return (False, season_id + "(未关注)")

        # 进行取关
        bili_database.delete_relation(4 + user_type, user_id, season_id)
        logger.info(f'[{__PLUGIN_NAME}]用户/群 <{user_id}> 取关番剧 <{season_id}> 成功')
        return (True, bili_database.query_info(4, season_id)[1]  + f"(season_id: {season_id})") 
    except BiliDatebaseError:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n取关番剧 <{season_id}> 时数据库发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"[{__PLUGIN_NAME}]" + exception_msg + traceback.format_exc())
        return (False, season_id + "(数据库错误)")
    
async def follow_telegram_list(
    user_id: int, 
    ep_id_list: List[str],
    user_type: int
    ) -> List[List[str]]:
    '''个人用户/群关注番剧

    Args:
        user_id (int): qq号/群号
        ep_id_list (List[str]): 关注的番剧号
        user_type (int): 0-个人用户，1-群

    Returns:
        List[List[str]]: [是否成功，信息]
    '''
    successList = []
    failList = []

    for ep_id in ep_id_list:
        if ep_id[0:2] != 'ep':
            failList.append(ep_id + "(错误参数)")
        else:
            ep_id = ep_id[2:]
            isSuccess, s = await follow_telegram(ep_id, user_id, user_type)
            if isSuccess:
                successList.append(s)
            else:
                failList.append(s)

    return [successList, failList] 

async def unfollow_telegram_list(
    user_id: int, 
    season_id_list: List[str],
    user_type: int
    ) -> List[List[str]]:
    '''个人用户/群取关番剧

    Args:
        user_id (int): qq号/群号
        season_id_list (List[str]): 取关的番剧号
        user_type (int): 0-个人用户，1-群

    Returns:
        List[List[str]]: [是否成功，信息]
    '''
    successList = []
    failList = []

    for season_id in season_id_list:
        isSuccess, s = await unfollow_telegram(season_id, user_id, user_type)
        if isSuccess:
            successList.append(s)
        else:
            failList.append(s)
    
    return [successList, failList]                 
                

            
            

        
    
            
