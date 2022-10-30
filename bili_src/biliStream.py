from typing import Tuple, List
import sys
import traceback
import nonebot
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageSegment
from .basicFunc import *
from .exception import *
import asyncio
from .bili_client import bili_client
from .bili_task import bili_task_manager
__PLUGIN_NAME = "[bilibilibot~直播]"
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
    liver_list = list(bili_task_manager.liver_list.values())
    
    sched_bot = nonebot.get_bot()
    
    """results = await asyncio.gather(
        *[bili_client.get_live_status(liver_info[0], liver_info[3]) for liver_info in liver_list],
        return_exceptions=True
    )"""

    results = await asyncio.gather(
        *[bili_client.get_live_status(liver_info["liver_uid"], liver_info["room_id"]) for liver_info in liver_list],
        return_exceptions=True
    )
    for i in range(len(liver_list)):
        if isinstance(results[i], tuple):
            if results[i][0] and not liver_list[i]["is_live"]:
                logger.info(f'[{__PLUGIN_NAME}]检测到主播 <{liver_list[i]["liver_name"]}> 已开播！')
                text_msg = '【直播动态】\n<{}>正在直播!\n标题: {}\n链接: {}'.format(liver_list[i]["liver_name"], results[i][1], f"https://live.bilibili.com/{liver_list[i]['room_id']}")
                reported_msg = text_msg + MessageSegment.image(results[i][2])
                logger.info(f'[{__PLUGIN_NAME}]向粉丝发送开播通知')
                bili_task_manager.update_liver_info(liver_list[i]["liver_uid"], True)
                #bili_database.update_info(1, 1, liver_list[i][0])

                user_list = liver_list[i]["user_follower"]
                await asyncio.gather(*[sched_bot.send_msg(message=reported_msg, user_id=user_id) for user_id in user_list])
                group_list = liver_list[i]["group_follower"]
                await asyncio.gather(*[sched_bot.send_msg(message=reported_msg, group_id=group_id) for group_id in group_list])

            elif not results[i][0] and liver_list[i]["is_live"]:
                logger.info(f'[{__PLUGIN_NAME}]检测到主播 <{liver_list[i]["liver_name"]}> 已下播')
                bili_task_manager.update_liver_info(liver_list[i]["liver_uid"], False)
                #bili_database.update_info(1, 0, liver_list[i][0])
        elif isinstance(results[i], (BiliAPIRetCodeError, BiliStatusCodeError, BiliConnectionError)):
            exception_msg = f'[错误报告]\n检测主播 <{liver_list[i]["liver_name"]}> 开播情况时发生错误\n错误类型: {type(results[i])}\n错误信息: {results[i]}'
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
        if uid not in bili_task_manager.liver_list:
            liver_name, room_id = await bili_client.init_liver_info(uid)
            
            bili_task_manager.add_liver_info(uid, liver_name, False, room_id)
            if user_type == 0:
                bili_task_manager.add_user_follower(1, uid, user_id)
            else:
                bili_task_manager.add_group_follower(1, uid, user_id)
            #bili_database.insert_relation(2 + user_type, uid, user_id)

            logger.info(f"{__PLUGIN_NAME}用户/群 <{user_id}> 关注主播 <{liver_name}> 成功")
            return (True, liver_name + f"(uid: {uid})")
        
        if user_type == 0 and user_id in bili_task_manager.liver_list[uid]["user_follower"] or \
            user_type == 1 and user_id in bili_task_manager.liver_list[uid]["group_follower"]:
            logger.debug(f'{__PLUGIN_NAME}主播 <{bili_task_manager.liver_list[uid]["liver_name"]}> 已关注')
            return (False, uid + "(已关注)")

        if user_type == 0:
            bili_task_manager.add_user_follower(1, uid, user_id)
        elif user_type == 1:
            bili_task_manager.add_group_follower(1, uid, user_id)

        logger.info(f"{__PLUGIN_NAME}用户/群 <{user_id}> 关注主播 <{bili_task_manager.liver_list[uid]['liver_name']}> 成功")
        return (True, bili_task_manager.liver_list[uid]["liver_name"] + f"(uid: {uid})")
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
        # 处理未关注
        if uid not in bili_task_manager.liver_list or \
            user_type == 0 and user_id not in bili_task_manager.liver_list[uid]["user_follower"] or \
            user_type == 1 and user_id not in bili_task_manager.liver_list[uid]["group_follower"]:
            logger.info(f'{__PLUGIN_NAME}用户/群 <{user_id}> 未关注主播 <{uid}>')
            return (False, uid + "(未关注)")

        # 进行取关
        liver_name = bili_task_manager.liver_list[uid]["liver_name"]
        if user_type == 0:
            bili_task_manager.remove_user_follower(1, uid, user_id)
        else:
            bili_task_manager.remove_group_follower(1, uid, user_id)
        
        return (True, liver_name + f"(uid: {uid})")
        
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