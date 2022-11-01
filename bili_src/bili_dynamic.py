from .exception import BiliConnectionError, BiliDatebaseError
import asyncio
from typing import Tuple, List
import sys
import traceback
import nonebot
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from .basicFunc import *
from .bili_client import bili_client
from .bili_task import bili_task_manager
from datetime import datetime
import json

__PLUGIN_NAME = "[bilibilibot~动态]"

# 视频
async def check_dynamic_update() -> None:
    """
    @description  :
    检查关注动态主是否更新新视频，如果更新则通知用户并更新缓存和数据库
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    schedBot = nonebot.get_bot()
    check_dynamic_list = bili_task_manager.get_dynamic_check_update_list()
    #logger.debug(f'{__PLUGIN_NAME}check_dynamic_list = {check_dynamic_list}')
    
    results = await asyncio.gather(
        *[bili_client.get_latest_dynamic(
            uid, 
            bili_task_manager.dynamic_list[uid]["pin_id_str"],
            bili_task_manager.dynamic_list[uid]["latest_timestamp"]
        ) for uid in check_dynamic_list],
        return_exceptions=True
    )
    
    for i in range(len(check_dynamic_list)):
        if isinstance(results[i], tuple):
            uid = check_dynamic_list[i]
            u_name = bili_task_manager.dynamic_list[uid]["u_name"]
            if results[i][0] is True:
                # 修改缓存中的置顶动态信息
                logger.debug(f'{__PLUGIN_NAME}原置顶动态为{bili_task_manager.dynamic_list[uid]["pin_id_str"]}')
                logger.debug(f'{__PLUGIN_NAME}新置顶动态为{results[i][2]}')
                
                
                logger.debug(f'{__PLUGIN_NAME}检测到<{u_name}>置顶动态发生了改变')
                bili_task_manager.update_dynamic_pin_id(uid, results[i][2])
            if results[i][1] is True:
                latest_timestamp = 0
                
                logger.info(f'{__PLUGIN_NAME}检测到<{u_name}>更新了动态')
                logger.debug(json.dumps(results[i][3], ensure_ascii=False, indent=4))

                info_msg = Message()
                text_msg = f"【B站动态】\n<{u_name}>更新了动态:\n"
                info_msg.append(text_msg)
                
                
                for dynamic_item in results[i][3]:
                    latest_timestamp = max(latest_timestamp, dynamic_item["timestamp"])
                    if dynamic_item["major_type"] in ("MAJOR_TYPE_DRAW", "MAJOR_TYPE_NONE", "MAJOR_TYPE_ARTICLE"):
                        dynamic_msg = Message()
                        dynamic_msg.append(MessageSegment.text("=============\n"))

                        # add time
                        dynamic_msg.append(MessageSegment.text(
                            "--" + 
                            datetime.fromtimestamp(dynamic_item["timestamp"]).strftime("%Y-%m-%d %H:%M")
                            + "--\n"))
                        # add text
                        dynamic_msg.append(MessageSegment.text(dynamic_item["text"] + "\n"))

                        # add image
                        for img_src in dynamic_item["image"]:
                            dynamic_msg.append(MessageSegment.image(img_src))
                        
                        # 如果是专栏,添加专栏信息
                        if dynamic_item["tag"] == "MAJOR_ARTICLE":
                            dynamic_msg.append(
                                MessageSegment.text(
                                    f'\n<{u_name}>发布了专栏 《{dynamic_item["article"]["title"]}》\n\
                                    链接: {dynamic_item["article"]["jump_url"]}\n'
                                )
                            )
                            dynamic_msg.append(MessageSegment.image(dynamic_item["article"]["cover"]))
                        # 添加附加信息
                        # 附加信息是投票
                        elif dynamic_item["tag"] == "ADD_VOTE":
                            dynamic_msg.append(MessageSegment.text("----附加信息----\n"))
                            dynamic_msg.append(MessageSegment.text(f'<{u_name}>发布了投票: <{dynamic_item["vote"]["desc"]}>\n'))
                        # 附加信息是视频
                        elif dynamic_item["tag"] == "ADD_UGC":
                            dynamic_msg.append(MessageSegment.text("----附加信息----\n"))
                            dynamic_msg.append(MessageSegment.text(f'标题: {dynamic_item["tgc"]["title"]}\n链接: {dynamic_item["tgc"]["jump_url"]}\n'))
                            dynamic_msg.append(MessageSegment.image(dynamic_item["tgc"]["cover"]))
                        # 附加信息是预约
                        elif dynamic_item["tag"] == "ADD_RESERVE":
                            dynamic_msg.append(MessageSegment.text("----附加信息----\n"))
                            dynamic_msg.append(MessageSegment.text(f'<{u_name}>发布了预约: <{dynamic_item["reserve"]["title"]}>\n{dynamic_item["reserve"]["desc"]}\n'))
                        dynamic_msg.append(MessageSegment.text("=============\n"))
                    
                        info_msg.extend(dynamic_msg)
                bili_task_manager.update_dynamic_latest_timestamp(uid, latest_timestamp)

                if len(info_msg) != 1:
                    user_list = bili_task_manager.dynamic_list[uid]["user_follower"]
                    for user_id in user_list:
                        await schedBot.send_msg(message=info_msg, user_id=user_id)
                    
                    group_list = bili_task_manager.dynamic_list[uid]["group_follower"]
                    for group_id in group_list:
                        await schedBot.send_msg(message=info_msg, group_id=group_id)

        elif isinstance(results[i], (BiliAPIRetCodeError, BiliStatusCodeError, BiliConnectionError)):
            exception_msg = f'[错误报告]\n检测动态主 <{check_dynamic_list[i]}> 更新情况时发生错误\n错误类型: {type(results[i])}\n错误信息: {results[i]}'
            logger.error(f"[{__PLUGIN_NAME}]" + exception_msg)

async def follow_dynamic(uid: str, user_id: str, user_type: int) -> Tuple[bool, str]:
    '''根据用户或群关注动态主，修改数据库

    Args:
        uid (str): 动态主的uid
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

        logger.debug(f'{__PLUGIN_NAME}uid = {uid}')
        if uid not in bili_task_manager.dynamic_list:
            logger.debug(f'{__PLUGIN_NAME}uid not in dynamic_list')
        else:
            logger.debug(f'{__PLUGIN_NAME}uid in dynamic_list: {bili_task_manager.dynamic_list[uid]}')
            
            
        if uid not in bili_task_manager.dynamic_list:
            u_name, pin_id_str, latest_timestamp = await bili_client.init_dynamic_info(uid)
            
            bili_task_manager.add_dynamic_info(uid, u_name, pin_id_str, latest_timestamp)
            logger.debug(f'{__PLUGIN_NAME}after update dynamic_list[uid] = {bili_task_manager.dynamic_list[uid]}')
        
            if user_type == 0:
                bili_task_manager.add_user_follower(3, uid, user_id)
            else:
                bili_task_manager.add_group_follower(3, uid, user_id)
            logger.debug(f'{__PLUGIN_NAME}after follow,  dynamic_list[uid] = {bili_task_manager.dynamic_list[uid]}')
        
            logger.info(f"{__PLUGIN_NAME}用户/群 <{user_id}> 关注动态主 <{u_name}> 成功")
            logger.debug(f"{uid}-{u_name}-{pin_id_str}-{latest_timestamp}")
            return (True, u_name + f"(uid: {uid})")
            
        u_name = bili_task_manager.dynamic_list[uid]["u_name"]
        # 处理已关注
        if user_type == 0 and user_id in bili_task_manager.dynamic_list[uid]["user_follower"] or \
            user_type == 1 and user_id in bili_task_manager.dynamic_list[uid]["group_follower"]:
            logger.info(f"{__PLUGIN_NAME}用户/群 <{user_id}> 已经关注了动态主 <{u_name}>")
            return (False, u_name + "(已关注)")

        # 进行关注
        if user_type == 0:
            bili_task_manager.add_user_follower(3, uid, user_id)
        elif user_type == 1:
            bili_task_manager.add_group_follower(3, uid, user_id)
        logger.info(f"{__PLUGIN_NAME}用户/群 <{user_id}> 关注动态主 <{u_name}> 成功")
        return (True, u_name + f"(uid: {uid})")
    except BiliAPI404Error:
        return (False, uid + "(uid错误)")
    except (BiliConnectionError, BiliAPIRetCodeError, BiliStatusCodeError):
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n获取动态主 <{uid}> B站信息发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())
        return (False, uid + "(网络错误)")
    except BiliDatebaseError:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n关注动态主 <{uid}>时数据库发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())
        return (False, uid + "(数据库错误)")
    except Exception:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n关注动态主 <{uid}>时发生意料之外的错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())
        return (False, uid + "(未知错误,请查看日志)")

async def unfollow_dynamic(uid: str, user_id: str, user_type: int) -> Tuple[bool, str]:
    '''根据个人用户或群取关动态主，修改up文件

    Args:
        uid (str): 动态主的uid
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
        #logger.debug(f"{uid}的关注列表{bili_task_manager.dynamic_list[uid]['user_follower']}")
        if uid not in bili_task_manager.dynamic_list or \
            user_type == 0 and user_id not in bili_task_manager.dynamic_list[uid]["user_follower"] or \
            user_type == 1 and user_id not in bili_task_manager.dynamic_list[uid]["group_follower"]:
            logger.info(f'{__PLUGIN_NAME}用户/群 <{user_id}> 未关注动态主 <{uid}>')
            return (False, uid + "(未关注)")
        
        # 进行取关
        u_name = bili_task_manager.dynamic_list[uid]["u_name"]
        if user_type == 0:
            bili_task_manager.remove_user_follower(3, uid, user_id)
        else:
            bili_task_manager.remove_group_follower(3, uid, user_id)
        logger.info(f'{__PLUGIN_NAME}用户/群 <{user_id}> 取关动态主 <{uid}> 成功')

        return (True, u_name  + f"(uid: {uid})") 
    except BiliDatebaseError:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n取关动态主 <{uid}> 时数据库发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())
        return (False, uid + "(数据库错误)")

async def follow_dynamic_list(
    user_id: int, 
    uid_list: List[str], 
    user_type: int
    ) -> List[List[str]]:
    '''个人用户/群关注动态主

    Args:
        user_id (int): qq号/群号
        uid_list (List[str]): 动态主的uid
        user_type (int): 0-个人用户，1-群        

    Returns:
        List[List[str]]: [[关注成功列表]，[关注失败列表]]
    '''
    successList = []
    failList = []
    
    for uid in uid_list:
        isSuccess, s = await follow_dynamic(uid, str(user_id), user_type)
        if isSuccess:
            successList.append(s)
        else:
            failList.append(s)

    return [successList, failList]

async def unfollow_dynamic_list(
    user_id: int, 
    uid_list: List[str],
    user_type: int
    ) -> List[List[str]]:
    '''个人用户/群取关动态主

    Args:
        user_id (int): qq号/群号
        uid_list (List[str]): 取关的动态主
        user_type (int): 0-个人用户，1-群

    Returns:
        List[List[str]]: [是否成功，信息]
    '''
    successList = []
    failList = []

    for uid in uid_list:
        isSuccess, s = await unfollow_dynamic(uid, str(user_id), user_type)
        if isSuccess:
            successList.append(s)
        else:
            failList.append(s)
    
    return [successList, failList]