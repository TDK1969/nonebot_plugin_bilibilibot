from typing import List, Tuple, Union
import json
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
PackagePath =  dirname(abspath(__file__))

__PLUGIN_NAME = "[B站整合~基础]"

async def createUserFile(userFile: str, nickName: str, streamers: List[str]=[], ups: List[str]=[], telegrams: List[str]=[]):
    '''创建用户/群文件

    Args:
        userFile (str): 文件路径
        nickName (str): 用户名/群名
        streamers (List[str], optional): 关注的主播. Defaults to [].
        ups (List[str], optional): 关注的up主. Defaults to [].
        telegrams (List[str], optional): 关注的番剧. Defaults to [].
    '''
    
    with open(userFile, 'w+', encoding='utf-8') as f:
            logger.debug(f'{__PLUGIN_NAME}群名为{nickName}')
            
            userInfo = [nickName, streamers, ups, telegrams]
            json.dump(userInfo, f, ensure_ascii=False)
    logger.debug(f'{__PLUGIN_NAME}用户文件{userFile}创建成功')

async def FollowModifyUserFile(userFile: str, successList: List[str], type: int):
    """
    @description  :
    根据用户的关注操作，修改用户/群文件
    ---------
    @param  :
    userFile:       用户/群的文件名
    successList:    成功关注的列表
    type:           1 - 主播, 2 - up主, 3 - 节目
    -------
    @Returns  :
    无返回值
    -------
    """
    with open(userFile, "r+", encoding='utf-8') as f:
        userInfo = json.load(f)
        userInfo[type] += successList
        # [nickname, [streamer], [up], [telegrams]]
        f.seek(0)
        f.truncate()
        json.dump(userInfo, f, ensure_ascii=False)
        logger.debug(f'{__PLUGIN_NAME}用户{userInfo[0]}文件更新成功')

async def UnfollowModifyUserFile(userFile: str, successList: List[str], type: int):
    """
    @description  :
    根据用户的取关操作，修改用户文件
    ---------
    @param  :
    userFile:       用户的文件名
    successList:    成功取关的列表
    type:           1 - 主播, 2 - up主, 3 - 节目
    -------
    @Returns  :
    无返回值
    -------
    """
    with open(userFile, "r+", encoding='utf-8') as f:
        userInfo = json.load(f)
        userInfo[type] = list(set(userInfo[type]) - set(successList))
            # [nickname, [streamer], [up], [telegrams]]
        f.seek(0)
        f.truncate()
        json.dump(userInfo, f, ensure_ascii=False)

async def parseB23Url(url: str) -> Tuple[bool, int, str]:
    """
    @description  :
    对b23.tv短链接进行转换
    ---------
    @param  :
    url: b23.tv类型的短链接
    -------
    @Returns  :
    返回一个元组
    [isSuccess, type, id]
    type: 1-直播房间号;2-up主uid;3-节目的epid
    -------
    """ 
    API = 'https://duanwangzhihuanyuan.bmcx.com/web_system/bmcx_com_www/system/file/duanwangzhihuanyuan/get/?ajaxtimestamp=1646565831920'
    payload = {'turl': url}
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url=API, data=payload)
    except Exception as e:
        raise BiliConnectionError(f"转换短连接{url}时发生网络错误:{e.args[0]}")
    if res.status_code != 200:
        raise BiliConnectionError(f"转换短连接{url}时连接出错:状态码={res.status_code}")

    if re.search("live.bilibili.com", res.text):
        roomNumber = re.search("live.bilibili.com/\d+", res.text)
        roomNumber = roomNumber.group()
        logger.debug(f'{__PLUGIN_NAME}短链接{url}是直播间链接,房间号为{roomNumber[18:]}')
        return (True, 1, roomNumber[18:])
    elif re.search("space.bilibili.com", res.text):
        uid = re.search("space.bilibili.com/\d+", res.text)
        uid = uid.group()
        logger.debug(f'{__PLUGIN_NAME}短链接{url}是个人空间,uid为{uid[19:]}')
        return (True, 2, uid[19:])
    elif re.search("www.bilibili.com/bangumi/play/ep", res.text):
        epid = re.search("www.bilibili.com/bangumi/play/ep\d+", res.text)
        epid = epid.group()
        logger.debug(f'{__PLUGIN_NAME}短链接{url}是番剧播放页面,epid为{"ep" + epid[32:]}')
        return (True, 3, "ep" + epid[32:])
    
    return (False, 0, '')

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


def CheckDir():
    """
    @description  :
    检查插件运行所需要的文件目录是否存在，不存在则创建
    ---------
    @param  :
    
    -------
    @Returns  :
    
    -------
    """
    
    baseDir = f'{PackagePath}/file/'

    if not os.path.exists(baseDir + 'source'):
        logger.debug(f'{__PLUGIN_NAME}source文件夹不存在')
        os.makedirs(baseDir + 'source')
        
    if not os.path.exists(baseDir + 'stream'):
        logger.debug(f'{__PLUGIN_NAME}stream文件夹不存在')
        os.makedirs(baseDir + 'stream')
    
    if not os.path.exists(baseDir + 'telegram'):
        logger.debug(f'{__PLUGIN_NAME}telegram文件夹不存在')
        os.makedirs(baseDir + 'telegram')
    
    if not os.path.exists(baseDir + 'up'):
        logger.debug(f'{__PLUGIN_NAME}up文件夹不存在')
        os.makedirs(baseDir + 'up')
        
    if not os.path.exists(baseDir + 'user'):
        logger.debug(f'{__PLUGIN_NAME}user文件夹不存在')
        os.makedirs(baseDir + 'user')
    
    if not os.path.exists(baseDir + 'group'):
        logger.debug(f'{__PLUGIN_NAME}group文件夹不存在')
        os.makedirs(baseDir + 'group')

