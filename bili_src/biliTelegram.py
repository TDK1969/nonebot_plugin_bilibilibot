from typing import Tuple, List
import sys
import asyncio
import traceback
import nonebot
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageSegment
from .basicFunc import *
from .exception import *
from .bili_client import bili_client
from .bili_task import bili_task_manager

__PLUGIN_NAME = "[bilibilibot~番剧]"
    
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
    
    telegram_list = list(bili_task_manager.telegram_list.values())
    telegram_list = [i for i in telegram_list if i["is_finish"] is False]
    sched_bot = nonebot.get_bot()
    # 只对未完结的番剧进行检查
    results = await asyncio.gather(
        *[bili_client.get_telegram_latest_episode(telegram_info["season_id"], telegram_info["episode"]) for telegram_info in telegram_list],
        return_exceptions=True
    )

    for i in range(len(telegram_list)):
        if isinstance(results[i], tuple):
            if results[i][0] is True:
                logger.info(f'[{__PLUGIN_NAME}]检测到影视剧 <{telegram_list[i]["telegram_title"]}> 更新')
                text_msg = "【B站动态】\n《{}》已更新第{}集\n标题: {}\n链接: {}\n".format(
                        telegram_list[i]["telegram_title"], results[i][1], results[i][2], results[i][3]
                    )
                bili_task_manager.update_telegram_info(telegram_list[i]["season_id"], results[i][1], results[i][5])
                cover_msg = MessageSegment.image(results[i][4])
                reported_msg = text_msg + cover_msg
                logger.info(f'[{__PLUGIN_NAME}]向关注用户发送更新通知')

                # 通知用户
                user_list = telegram_list[i]["user_follower"]
                await asyncio.gather(*[sched_bot.send_msg(message=reported_msg, user_id=user_id) for user_id in user_list])
            
                group_list = telegram_list[i]["group_follower"]
                await asyncio.gather(*[sched_bot.send_msg(message=reported_msg, group_id=group_id) for group_id in group_list])
            
        elif isinstance(results[i], (BiliAPIRetCodeError, BiliStatusCodeError, BiliConnectionError)):
            exception_msg = f'[错误报告]\n检测番剧 <{telegram_list[i]["telegram_title"]}> 更新情况时发生错误\n错误类型: {type(results[i])}\n错误信息: {results[i]}'
            logger.error(f"[{__PLUGIN_NAME}]" + exception_msg)
        
async def follow_telegram(id_prefix: str, telegram_id: int, user_id: str, user_type: int) -> Tuple[bool, str]:
    '''根据用户关注节目，修改节目的文件

    Args:
        id_prefix (str): ep | ss | md
        telegram_id (int): 节目的id
        user_id (str): 用户的qq号/群号
        user_type (int): 0-个人用户，1-群号

    Returns:
        Tuple[bool, str]: [是否成功，信息]
    '''
    
    try:
        if id_prefix == "ep":
            res = await bili_client.init_telegram_info_by_ep_id(telegram_id)
        elif id_prefix == "ss":
            res = await bili_client.init_telegram_info_by_season_id(telegram_id)
        elif id_prefix == "md":
            res = await bili_client.init_telegram_info_by_media_id(telegram_id)
        else:
            return (False, telegram_id + "(番剧id错误)")
        
        season_id, telegram_title, episode, is_finish = res
        season_id = str(season_id)
        logger.debug(f'{__PLUGIN_NAME}{bili_task_manager.telegram_list}')
        
        if season_id not in bili_task_manager.telegram_list:
            logger.debug(f'{__PLUGIN_NAME}{season_id}不在任务列表中存在')
            bili_task_manager.add_telegram_info(season_id, telegram_title, episode, is_finish)
            if user_type == 0:
                bili_task_manager.add_user_follower(2, season_id, user_id)
            else:
                bili_task_manager.add_group_follower(2, season_id, user_id)
            
            logger.info(f"[{__PLUGIN_NAME}]用户/群 <{user_id}> 关注番剧 <{telegram_title}> 成功")
            return (True, telegram_title + f"(season_id: {season_id})")
        
        if user_type == 0 and user_id in bili_task_manager.telegram_list[season_id]["user_follower"] or \
            user_type == 1 and user_id in bili_task_manager.telegram_list[season_id]["group_follower"]:
            logger.debug(f'{__PLUGIN_NAME}番剧 <{bili_task_manager.telegram_list[season_id]["telegram_title"]}> 已关注')
            return (False, season_id + "(已关注)")

        logger.debug(f'{__PLUGIN_NAME}进行关注{season_id}')
        
        if user_type == 0:
            bili_task_manager.add_user_follower(2, season_id, user_id)
        else:
            bili_task_manager.add_group_follower(2, season_id, user_id)
        logger.info(f"[{__PLUGIN_NAME}]用户/群 <{user_id}> 关注番剧 <{telegram_title}> 成功")
        return (True, telegram_title + f"(season_id: {season_id})")
 
    except BiliAPI404Error:
        return (False, f"{id_prefix}{telegram_id}" + "(番剧id错误)")
    except (BiliConnectionError, BiliAPIRetCodeError, BiliStatusCodeError):
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n获取番剧 <{id_prefix}{telegram_id}> 信息发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"[{__PLUGIN_NAME}]" + exception_msg + traceback.format_exc())
        return (False, f"{id_prefix}{telegram_id}" + "(网络错误)")
    except BiliDatebaseError:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n关注番剧 <{season_id}> 时数据库发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"[{__PLUGIN_NAME}]" + exception_msg + traceback.format_exc())
        return (False, season_id + "(数据库错误)")
    except Exception:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n关注番剧 <{id_prefix}{telegram_id}> 时发生意料之外的错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"[{__PLUGIN_NAME}]" + exception_msg + traceback.format_exc())
        return (False, f"{id_prefix}{telegram_id}" + "(未知错误,请查看日志)")
        
async def unfollow_telegram(season_id: str, user_id: str, user_type: int) -> Tuple[bool, str]:
    '''根据用户/群取关节目，修改节目文件

    Args:
        season_id (str): 节目的ID
        user_id (str): 用户qq号/群号
        user_type (int): 0-个人用户，1-群号

    Returns:
        Tuple[bool, str]: [是否成功, 信息]
    '''
    if season_id[:2] != "ss" and not season_id[2:].isdigit():
        return (False, season_id + "(错误参数)")
    
    season_id = season_id[2:]
    logger.debug(f'{__PLUGIN_NAME}{bili_task_manager.telegram_list}')
    
    try:
        if season_id not in bili_task_manager.telegram_list or \
            user_type == 0 and user_id not in bili_task_manager.telegram_list[season_id]["user_follower"] or \
            user_type == 1 and user_id not in bili_task_manager.telegram_list[season_id]["group_follower"]:
            logger.info(f'{__PLUGIN_NAME}用户/群 <{user_id}> 未关注番剧 <{season_id}>')
            return (False, season_id + "(未关注)")

        telegram_title = bili_task_manager.telegram_list[season_id]["telegram_title"]
        if user_type == 0:
            bili_task_manager.remove_user_follower(2, season_id, user_id)
        else:
            bili_task_manager.remove_group_follower(2, season_id, user_id)
        
        return (True, telegram_title + f"(season_id: ss{season_id})")
        
    except BiliDatebaseError:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n取关番剧 <{season_id}> 时数据库发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"[{__PLUGIN_NAME}]" + exception_msg + traceback.format_exc())
        return (False, season_id + "(数据库错误)")
    
async def follow_telegram_list(
    user_id: int, 
    telegram_id_list: List[str],
    user_type: int
    ) -> List[List[str]]:
    '''个人用户/群关注番剧

    Args:
        user_id (int): qq号/群号
        telegram_id_list (List[str]): 关注的番剧号
        user_type (int): 0-个人用户，1-群

    Returns:
        List[List[str]]: [是否成功，信息]
    '''
    # 在该函数中同时对telegram_id, season_id, media_id进行区分和统一处理
    success_list = []
    fail_list = []
    prefix_type = ('ep', 'ss', "md")
    valid_telegram_id_list = []
    for telegram_id in telegram_id_list:
        logger.debug(f'{__PLUGIN_NAME}telegram_id = {telegram_id}')
        
        if telegram_id[:2] not in prefix_type or not telegram_id[2:].isdigit():
            fail_list.append(telegram_id + "(错误参数)")
        else:
            valid_telegram_id_list.append(telegram_id)
    logger.debug(f'{__PLUGIN_NAME}valid list = {valid_telegram_id_list}')
    
    results = await asyncio.gather(
        *[follow_telegram(telegram_id[:2], int(telegram_id[2:]), str(user_id), user_type) for telegram_id in valid_telegram_id_list],
        return_exceptions=True
    )

    for is_success, msg in results:
        if is_success:
            success_list.append(msg)
        else:
            fail_list.append(msg)
    
    return [success_list, fail_list] 

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
    success_list = []
    fail_list = []

    for season_id in season_id_list:
        isSuccess, s = await unfollow_telegram(season_id, str(user_id), user_type)
        if isSuccess:
            success_list.append(s)
        else:
            fail_list.append(s)
    
    return [success_list, fail_list]                 
                

            
            

        
    
            
