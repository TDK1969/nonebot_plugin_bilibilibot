from nonebot import get_driver, on_command, on_message, require, permission, get_bot
from nonebot.rule import to_me
from nonebot.log import logger
from nonebot.rule import to_me, regex

from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Message, MessageSegment, MessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND, GROUP_MEMBER
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from nonebot.params import CommandArg


from .config import Config

from .biliStream import *
from .biliVideo import *
from .biliTelegram import *
from .basicFunc import *
from .rule import groupMessageRule, privateMessageRule

import os
import json
import sys
import re
from typing import Union

global_config = get_driver().config
config = Config.parse_obj(global_config)

__PLUGIN_NAME = "[B站整合]"

ALL_PERMISSION = GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND

followStreamerCommand = on_command("关注主播", permission=ALL_PERMISSION)
@followStreamerCommand.handle()
async def followStreamerCommandHandler(event: Union[PrivateMessageEvent, GroupMessageEvent], args: Message = CommandArg()):
    uidList = args.extract_plain_text().split()
    if isinstance(event, PrivateMessageEvent):
        successList, failList = await FollowStreamers(event, event.sender.user_id, uidList, 0)
    if isinstance(event, GroupMessageEvent):
        successList, failList = await FollowStreamers(event, event.group_id, uidList, 1)
    await followStreamerCommand.finish(f"关注成功:\n{successList}\n关注失败:\n{failList}")

unfollowStreamerCommand = on_command("取关主播", aliases={"切割主播"}, permission=ALL_PERMISSION)
@unfollowStreamerCommand.handle()
async def unfollowStreamerCommandHandler(event: Union[PrivateMessageEvent, GroupMessageEvent], args: Message = CommandArg()):
    uidList = args.extract_plain_text().split()
    if isinstance(event, PrivateMessageEvent):
        successList, failList = await UnfollowStreamers(event, event.sender.user_id, uidList, 0)
    if isinstance(event, GroupMessageEvent):
        successList, failList = await UnfollowStreamers(event, event.group_id, uidList, 1)
    await unfollowStreamerCommand.finish(f"取关成功:\n{successList}\n取关失败:\n{failList}")

listFollowingCommand = on_command("查询关注", aliases={"查询成分"}, permission=ALL_PERMISSION)
@listFollowingCommand.handle()
async def listFollowingCommandHandler(event: Union[PrivateMessageEvent, GroupMessageEvent], args: Message = CommandArg()):
    inputArgs = args.extract_plain_text().split()
    defaultArgs = ['直播', 'up主', '番剧']

    if isinstance(event, PrivateMessageEvent):
        userID = event.sender.user_id
        userFile = f"{PackagePath}/file/user/{userID}.json"
    elif isinstance(event, GroupMessageEvent):
        groupID = event.group_id
        userFile = f"{PackagePath}/file/group/{groupID}.json"
    
    exceptArgs = set(inputArgs) - set(defaultArgs)
    if len(exceptArgs) != 0:
        logger.info(f'{__PLUGIN_NAME}查询失败，存在错误参数: {exceptArgs}')
        await listFollowingCommand.finish(f"查询失败，存在错误参数:{exceptArgs}\n请正确输入命令,例如: '查询成分 直播' 或 '查询成分 直播 up主 番剧'")
    
    if os.path.exists(userFile):
        with open(userFile, "r+") as f:
            userInfo = json.load(f)

        if not inputArgs:
            inputArgs = defaultArgs
        if '直播' in inputArgs:
            if userInfo[1]:
                textMsg = '关注的主播:\n'
                for info in userInfo[1]:
                    textMsg += '> ' + info + '\n'
            else:
                textMsg = '无关注的主播'
            await listFollowingCommand.send(textMsg)
        if 'up主' in inputArgs:
            if userInfo[2]:
                textMsg = '关注的up主\n'
                for info in userInfo[2]:
                    textMsg += '> ' + info + '\n'
            else:
                textMsg = '无关注的up主'
            await listFollowingCommand.send(textMsg)
        if '番剧' in inputArgs:
            if userInfo[3]:
                textMsg = '关注的番剧\n'
                for info in userInfo[3]:
                    textMsg += '> '+ info + '\n'
            else:
                textMsg = '无关注的番剧'
            await listFollowingCommand.send(textMsg)
        await listFollowingCommand.finish()
    else:
        logger.info(f'{__PLUGIN_NAME}用户文件不存在，准备创建')
        name = event.sender.nickname
        if isinstance(event, GroupMessageEvent):
            bot = get_bot()
            groupInfo = await bot.get_group_info(group_id=id)
            name = groupInfo["group_name"]
        await createUserFile(userFile, nickName=name)
        await listFollowingCommand.finish("关注列表为空")

followUpCommand = on_command("关注up", permission=ALL_PERMISSION)
@followUpCommand.handle()
async def followUpCommandHandler(event: Union[PrivateMessageEvent, GroupMessageEvent], args: Message = CommandArg()):
    uidList = args.extract_plain_text().split() 
    if isinstance(event, PrivateMessageEvent):
        successList, failList = await FollowUp(event, event.sender.user_id, uidList, 0)
    if isinstance(event, GroupMessageEvent):
        successList, failList = await FollowUp(event, event.group_id, uidList, 1)
    await followUpCommand.finish(f"关注成功:\n{successList}\n关注失败:\n{failList}")

unfollowUpCommand = on_command("取关up", permission=ALL_PERMISSION)
@unfollowUpCommand.handle()
async def unfollowUpCommandHandler(event: Union[PrivateMessageEvent, GroupMessageEvent], args: Message = CommandArg()):
    uidList = args.extract_plain_text().split()
    if isinstance(event, PrivateMessageEvent):
        successList, failList = await UnfollowUp(event, event.sender.user_id, uidList, 0)
    if isinstance(event, GroupMessageEvent):
        successList, failList = await UnfollowUp(event, event.group_id, uidList, 1)
    await unfollowUpCommand.finish(f"取关成功:\n{successList}\n取关失败:\n{failList}")

followTelegramCommand = on_command("关注番剧", permission=ALL_PERMISSION)
@followTelegramCommand.handle()
async def followTelegramCommandHandler(event: Union[PrivateMessageEvent, GroupMessageEvent], args: Message = CommandArg()):
    epIDList = args.extract_plain_text().split()
    if isinstance(event, PrivateMessageEvent):
        successList, failList = await FollowTelegram(event, event.sender.user_id, epIDList, 0)
    if isinstance(event, GroupMessageEvent):
        successList, failList = await FollowTelegram(event, event.group_id, epIDList, 1)
    await followTelegramCommand.finish(f"关注成功:\n{successList}\n关注失败:\n{failList}")

unfollowTelegramCommand = on_command("取关番剧", permission=ALL_PERMISSION)
@unfollowTelegramCommand.handle()
async def unfollowTelegramCommandHandler(event: Union[PrivateMessageEvent, GroupMessageEvent], args: Message = CommandArg()):
    seasonIDs = args.extract_plain_text().split()
    if isinstance(event, PrivateMessageEvent):
        successList, failList = await UnfollowTelegram(event, event.sender.user_id, seasonIDs, 0)
    if isinstance(event, GroupMessageEvent):
        successList, failList = await UnfollowTelegram(event, event.group_id, seasonIDs, 1)
    await unfollowTelegramCommand.finish(f"取关成功:\n{successList}\n取关失败:\n{failList}")

followUpByShare = on_message(
    rule=regex('\[CQ:json,[\w\W]*"appid":100951776[\w\W]*space.bilibili.com[\w\W]*[\w\W]*\]') & privateMessageRule, 
    permission=PRIVATE_FRIEND
    )
@followUpByShare.handle()
async def upShareHandler(event: PrivateMessageEvent):
    '''响应用户分享up主空间连接

    Args:
        event (PrivateMessageEvent): 消息事件
    '''

    sJson = event.get_message()[-1].get('data')
    data = json.loads(sJson['data'])
    uid = data['meta']['news']['jumpUrl'].split('?')[0].split('/')[-1]
    
    successList, failList = await FollowUp(event, event.sender.user_id, [uid], 0)
    
    if successList:
        await followUpByShare.finish(f"关注up成功: <{successList[0]}>")
    elif failList:
        await followUpByShare.finish(f"关注up失败: <{failList[0]}>")

followStreamerByShare = on_message(
    rule=regex('^\[CQ:json,[\w\W]*"appid":100951776[\w\W]*live.bilibili.com[\w\W]*') & privateMessageRule,
    permission=PRIVATE_FRIEND
    )
@followStreamerByShare.handle()
async def streamerShareHandler(event: PrivateMessageEvent):
    '''响应个人用户的直播间分享

    Args:
        event (PrivateMessageEvent): 消息事件
    '''
    sJson = event.get_message()[-1].get('data')
    data = json.loads(sJson['data'])
    roomNumber = data['meta']['news']['jumpUrl'].split('?')[0].split('/')[-1]
    
    try:
        isUidSuccess, uid = GetUidByRoomNumber(roomNumber)
    except Exception:
        ex_type, ex_val, _ = sys.exc_info()
        logger.error(f'{__PLUGIN_NAME}获取主播 <{uid}> 信息时发生错误')
        logger.error(f'{__PLUGIN_NAME}错误类型: {ex_type},错误值: {ex_val}')
        await followStreamerByShare.finish('关注失败: 连接错误')
    else:
        if isUidSuccess:
            successList, failList = await FollowStreamers(event, event.sender.user_id, [uid], 0)

            if successList:
                await followUpByShare.finish(f"关注主播成功: <{successList[0]}>")
            elif failList:
                await followUpByShare.finish(f"关注主播失败: <{failList[0]}> ")

        else:
            await followStreamerByShare.finish(f'关注失败: 非法uid')

followTelegramByShare = on_message(
    rule = regex('^\[CQ:json[\w\W]*"appid":100951776[\w\W]*www.bilibili.com\/bangumi\/play\/[\w\W]*') & privateMessageRule,
    permission=PRIVATE_FRIEND
)
@followTelegramByShare.handle()
async def telegramShareHandler(event: PrivateMessageEvent):
    '''响应用户分享番剧页面

    Args:
        event (PrivateMessageEvent): 消息事件
    '''
    sJson = event.get_message()[-1].get('data')
    data = json.loads(sJson['data'])
    epID = data['meta']['detail_1']['qqdocurl'].split('?')[0].split('/')[-1]
    epID = epID[2:]
    
    
    successList, failList = await FollowTelegram(event, event.sender.user_id, [epID], 0)
    
    if successList:
        await followUpByShare.finish(f"关注番剧成功: <{successList[0]}>")
    elif failList:
        await followUpByShare.finish(f"关注番剧失败: <{failList[0]}> ")

followByShareB23Url = on_message(
    rule = regex('^\[CQ:json[\w\W]*"appid":100951776[\w\W]*b23.tv[\w\W]*') & privateMessageRule,
    permission=PRIVATE_FRIEND
)
@followByShareB23Url.handle()
async def b23UrlShareHandler(event: PrivateMessageEvent):
    sJson = event.get_message()[-1].get('data')
    shortLink = re.search("https:\/\/b23.tv\/\w+", sJson['data'])
    b23Url = shortLink.group()
    
    msgType = 0
    userID = event.sender.user_id
    
    try:
        isSuccess, idType, id = parseB23Url(b23Url)
    except Exception:
        ex_type, ex_val, _ = sys.exc_info()
        logger.error(f'{__PLUGIN_NAME}解析短链接 <{b23Url}> 时发生错误')
        logger.error(f'{__PLUGIN_NAME}错误类型: {ex_type},错误值: {ex_val}')
        await followByShareB23Url.finish('关注失败: 连接错误')
    else:
        if isSuccess:
            if idType == 1:
                try:
                    isUidSuccess, uid = GetUidByRoomNumber(id)
                except Exception:
                    ex_type, ex_val, _ = sys.exc_info()
                    logger.error(f'{__PLUGIN_NAME}获取主播 <{uid}> 信息时发生错误')
                    logger.error(f'{__PLUGIN_NAME}错误类型: {ex_type},错误值: {ex_val}')
                    await followByShareB23Url.finish('关注失败: 连接错误')
                else:
                    if isUidSuccess:
                        successList, failList = await FollowStreamers(event, userID, [uid], msgType)
                        if successList:
                            await followByShareB23Url.finish(f"关注成功: {successList[0]}")
                        elif failList:
                            await followByShareB23Url.finish(f"关注失败: {failList[0]}")
                    else:
                        await followByShareB23Url.finish(f'关注失败: 非法uid')

            elif idType == 2:
                successList, failList = await FollowUp(event, userID, [uid], msgType)
                if successList:
                    await followByShareB23Url.finish(f"关注成功: {successList[0]}")
                elif failList:
                    await followByShareB23Url.finish(f"关注失败: {failList[0]}")

            elif idType == 3:
                successList, failList = await FollowTelegram(event, userID, [uid], msgType)
                if successList:
                    await followByShareB23Url.finish(f"关注成功: {successList[0]}")
                elif failList:
                    await followByShareB23Url.finish(f"关注失败: {failList[0]}")
        else:
            await followByShareB23Url.finish(f"关注失败: 非法短链接{b23Url}")

helpCommand = on_command("help", permission=ALL_PERMISSION, aliases={'帮助'})
@helpCommand.handle()
async def sendHelpMsg(event: MessageEvent):
    userID = event.sender.user_id
    helpMsg = ""
    with open(f'{PackagePath}/file/source/help.json', 'r') as f:
        helpMsg = json.load(f)
    await helpCommand.finish(helpMsg)

publicBroacast = on_command("broacast", aliases={'广播'}, permission=permission.SUPERUSER)
@publicBroacast.handle()
async def sendBroacast(event: MessageEvent):
    announcement = ""
    announcementPath = f'{PackagePath}/file/source/announcement.json'
    if os.path.exists(announcementPath):
        with open(announcementPath, 'r') as f:
            announcement = json.load(f)
            
        users = GetAllUser()
        await SendMsgToUsers(announcement, users)

        groups = GetAllGroup()
        await SendMsgToGroups(announcement, groups)

        await publicBroacast.finish("公告发送成功")
    else:
        logger.debug(f'{__PLUGIN_NAME}公告文件不存在')
        await publicBroacast.finish("公告发送失败: 公告文件不存在") 

scheduler = require("nonebot_plugin_apscheduler").scheduler
scheduler.add_job(CheckBiliStream, "interval", seconds=10, id="biliStream", misfire_grace_time=90)
scheduler.add_job(CheckUpUpdate, "interval", minutes=1, id="biliUp", misfire_grace_time=90)
scheduler.add_job(CheckTeleUpdate, "interval", minutes=5, id="biliTele", misfire_grace_time=90)

CheckDir()