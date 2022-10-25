from .exception import BiliConnectionError, BiliDatebaseError
import asyncio
from typing import Tuple, List
import sys
import traceback
import nonebot
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageSegment
from .basicFunc import *
from .bili_client import bili_client
from .bili_task import bili_task_manager

__PLUGIN_NAME = "[bilibilibot~视频]"

# 视频
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
    schedBot = nonebot.get_bot()
    #assert status == True, "数据库发生错误"
    check_up_list = bili_task_manager.get_up_check_update_list()
    results = await asyncio.gather(
        *[bili_client.get_latest_video(uid, latest_timestamp) for uid, latest_timestamp in check_up_list],
        return_exceptions=True
    )
    
    for i in range(len(check_up_list)):
        if isinstance(results[i], tuple):
            if results[i][0] is True:
                up_uid = check_up_list[i][0]
                up_name = bili_task_manager.up_list[up_uid]["up_name"]

                logger.info(f'{__PLUGIN_NAME}检测到up主<{up_name}>更新了视频')
                textMsg = f"【B站动态】\n <{up_name}> 更新了视频\n标题: {results[i][2]}\n链接: https://www.bilibili.com/video/{results[i][1]}"
                
                bili_task_manager.update_up_info(up_uid, results[i][3])

                user_list = bili_task_manager.up_list[up_uid]["user_follower"]
                for user_id in user_list:
                    await schedBot.send_msg(message=textMsg + MessageSegment.image(results[i][4]), user_id=user_id)
                
                group_list = bili_task_manager.up_list[up_uid]["group_follower"]
                for group_id in group_list:
                    await schedBot.send_msg(message=textMsg + MessageSegment.image(results[i][4]), group_id=group_id)
        elif isinstance(results[i], (BiliAPIRetCodeError, BiliStatusCodeError, BiliConnectionError)):
            exception_msg = f'[错误报告]\n检测up主 <{up_name}> 更新情况时发生错误\n错误类型: {type(results[i])}\n错误信息: {results[i]}'
            logger.error(f"[{__PLUGIN_NAME}]" + exception_msg)

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
    
    uid = str(int(uid))
    
    try:
        
        # up信息不存在于数据库,对数据库进行更新
        if uid not in bili_task_manager.up_list:
            up_name, latest_timestamp = await bili_client.init_up_info(uid)
            
            if up_name:
                bili_task_manager.add_up_info(uid, up_name, latest_timestamp)
                if user_type == 0:
                    bili_task_manager.add_user_follower(0, uid, user_id)
                else:
                    bili_task_manager.add_group_follower(0, uid, user_id)
               
                logger.info(f"{__PLUGIN_NAME}用户/群 <{user_id}> 关注主播 <{up_name}> 成功")
                return (True, up_name + f"(uid: {uid})")
            else:
                logger.info(f'{__PLUGIN_NAME}up({uid})不存在，请检查uid')
                return (False, uid + "(uid错误)")
        up_name = bili_task_manager.up_list[uid]["up_name"]
        # 处理已关注
        if user_type == 0 and user_id in bili_task_manager.up_list[uid]["user_follower"] or \
            user_type == 1 and user_id in bili_task_manager.up_list[uid]["group_follower"]:
            logger.info(f"{__PLUGIN_NAME}用户/群 <{user_id}> 已经关注了up <{up_name}>")
            return (False, up_name + "(已关注)")

        # 进行关注
        if user_type == 0:
            bili_task_manager.add_user_follower(0, uid, user_id)
        elif user_type == 1:
            bili_task_manager.add_group_follower(0, uid, user_id)
        logger.info(f"{__PLUGIN_NAME}用户/群 <{user_id}> 关注up <{up_name}> 成功")
        return (True, up_name + f"(uid: {uid})")
    except BiliAPI404Error:
        return (False, uid + "(uid错误)")
    except (BiliConnectionError, BiliAPIRetCodeError, BiliStatusCodeError):
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
        logger.debug(f"{uid}的关注列表{bili_task_manager.up_list[uid]['user_follower']}")
        if uid not in bili_task_manager.up_list or \
            user_type == 0 and user_id not in bili_task_manager.up_list[uid]["user_follower"] or \
            user_type == 1 and user_id not in bili_task_manager.up_list[uid]["group_follower"]:
            logger.info(f'{__PLUGIN_NAME}用户/群 <{user_id}> 未关注up <{uid}>')
            return (False, uid + "(未关注)")
        
        # 进行取关
        up_name = bili_task_manager.up_list[uid]["up_name"]
        if user_type == 0:
            bili_task_manager.remove_user_follower(0, uid, user_id)
        else:
            bili_task_manager.remove_group_follower(0, uid, user_id)
        logger.info(f'{__PLUGIN_NAME}用户/群 <{user_id}> 取关up <{uid}> 成功')

        return (True, up_name  + f"(uid: {uid})") 
    except BiliDatebaseError:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n取关up主 <{uid}> 时数据库发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())
        return (False, uid + "(数据库错误)")

async def follow_up_list(
    user_id: int, 
    uid_list: List[str], 
    user_type: int
    ) -> List[List[str]]:
    '''个人用户/群关注up主

    Args:
        user_id (int): qq号/群号
        uid_list (List[str]): up主的uid
        user_type (int): 0-个人用户，1-群        

    Returns:
        List[List[str]]: [[关注成功列表]，[关注失败列表]]
    '''
    successList = []
    failList = []
    
    for uid in uid_list:
        isSuccess, s = await follow_up(uid, str(user_id), user_type)
        if isSuccess:
            successList.append(s)
        else:
            failList.append(s)

    return [successList, failList]

async def unfollow_up_list(
    user_id: int, 
    uid_list: List[str],
    user_type: int
    ) -> List[List[str]]:
    '''个人用户/群取关up主

    Args:
        user_id (int): qq号/群号
        uid_list (List[str]): 取关的up主
        user_type (int): 0-个人用户，1-群

    Returns:
        List[List[str]]: [是否成功，信息]
    '''
    successList = []
    failList = []

    for uid in uid_list:
        isSuccess, s = await unfollow_up(uid, str(user_id), user_type)
        if isSuccess:
            successList.append(s)
        else:
            failList.append(s)
    
    return [successList, failList]