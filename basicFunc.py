from typing import List, Tuple
import json
import re
import requests
import os
from nonebot import get_bot
from nonebot.log import logger
from os.path import abspath, dirname

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
    
    with open(userFile, 'w+') as f:
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
    with open(userFile, "r+") as f:
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
    with open(userFile, "r+") as f:
        userInfo = json.load(f)
        userInfo[type] = list(set(userInfo[type]) - set(successList))
            # [nickname, [streamer], [up], [telegrams]]
        f.seek(0)
        f.truncate()
        json.dump(userInfo, f, ensure_ascii=False)

def parseB23Url(url: str) -> Tuple[bool, int, str]:
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
    res = requests.post(url=API, data=payload)
    assert res.status_code == 200, f'转换短链接时发生异常，status_code = {res.status_code}'

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
        logger.debug(f'{__PLUGIN_NAME}短链接{url}是番剧播放页面,epid为{epid[32:]}')
        return (True, 3, epid[32:])
    
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
    
    users = os.listdir(f'{PackagePath}/file/user')
    result = []
    for user in users:
        userID = user.split('.')[0]
        result.append(userID)
    return result

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
    
    users = os.listdir(f'{PackagePath}/file/group')
    result = []
    for user in users:
        userID = user.split('.')[0]
        result.append(userID)
    return result

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

