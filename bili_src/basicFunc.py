from typing import List, Tuple, Union
import re
import httpx
import os
import sys
import traceback
from nonebot import get_bot
from nonebot.log import logger
from os.path import abspath, dirname
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from .db import bili_database
from .exception import *

__PLUGIN_NAME = "[bilibilibot~基础]"

def GetAllUser() -> List[str]:
    """
    @description  :
    获取所有用户
    ---------
    @param  :
    无
    -------
    @Returns  :
    返回所有用户qq号组成的列表
    -------
    """
    qq_users = bili_database.query_all(3)
    return [i[0] for i in qq_users]

def GetAllGroup() -> List[str]:
    """
    @description  :
    获取所有群
    ---------
    @param  :
    无
    -------
    @Returns  :
    返回所有群号组成的列表
    -------
    """

    qq_groups = bili_database.query_all(4)
    return [i[0] for i in qq_groups]

async def SendMsgToUsers(msg: str, users: List[str]):
    """
    @description  :
    向所有用户发送公告
    ---------
    @param  :
    msg: 内容
    users: 用户的qq列表
    -------
    @Returns  :
    无
    -------
    """
    
    bot = get_bot()
    for user in users:
        await bot.send_msg(message=msg, user_id = user)
    
async def SendMsgToGroups(msg: str, groups: List[str]):
    '''向所有群组发送公告

    Args:
        msg (str): 公告内容
        groups (List[str]): 群组列表
    '''
    
    bot = get_bot()
    for group in groups:
        await bot.send_msg(message=msg, group_id = group)

async def create_user(event: Union[PrivateMessageEvent, GroupMessageEvent]) -> None:
    '''接受消息后,创建用户

    Args:
        event (Union[PrivateMessageEvent, GroupMessageEvent]): 消息事件
    '''

    user_type = 0 if isinstance(event, PrivateMessageEvent) else 1
    user_id = event.sender.user_id if user_type == 0 else event.group_id
    try:
        user_info = bili_database.query_info(user_type, str(user_id))
        if not user_info:
            logger.info(f'{__PLUGIN_NAME}用户{user_id}不存在于数据库,即将创建')
            name = event.sender.nickname
            if user_type == 1:
                bot = get_bot()
                group_info = await bot.get_group_info(group_id=user_id)
                name = group_info["group_name"]
            bili_database.insert_info(user_type, user_id, name)
    except Exception as _:
            ex_type, ex_val, _ = sys.exc_info()
            exception_msg = '【错误报告】\n创建用户时发生错误\n错误类型: {}\n错误值: {}\n'.format(ex_type, ex_val)
            logger.error(f"{__PLUGIN_NAME}\n" + exception_msg + traceback.format_exc())

