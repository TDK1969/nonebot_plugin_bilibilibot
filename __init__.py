from nonebot import get_driver, on_command, on_message, require, permission, get_bot
from nonebot.log import logger
from nonebot.rule import regex

from nonebot.adapters.onebot.v11 import Message, MessageSegment, MessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND, GROUP_MEMBER
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
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

__PLUGIN_NAME = "[bilibilibot]"

ALL_PERMISSION = GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER

follow_liver_command = on_command("关注主播", permission=ALL_PERMISSION)
@follow_liver_command.handle()
async def follow_liver_command_handler(event: Union[PrivateMessageEvent, GroupMessageEvent], args: Message = CommandArg()):
    uid_list = args.extract_plain_text().split()
    await create_user(event)
    if isinstance(event, PrivateMessageEvent):
        success_list, fail_list = await follow_liver_list(event.sender.user_id, uid_list, 0)
    if isinstance(event, GroupMessageEvent):
        success_list, fail_list = await follow_liver_list(event.group_id, uid_list, 1)
    await follow_liver_command.finish(f"关注成功:\n{success_list}\n关注失败:\n{fail_list}")

unfollow_liver_command = on_command("取关主播", aliases={"切割主播"}, permission=ALL_PERMISSION)
@unfollow_liver_command.handle()
async def unfollow_liver_command_handler(event: Union[PrivateMessageEvent, GroupMessageEvent], args: Message = CommandArg()):
    uid_list = args.extract_plain_text().split()
    await create_user(event)
    if isinstance(event, PrivateMessageEvent):
        success_list, fail_list = await unfollow_liver_list(event.sender.user_id, uid_list, 0)
    if isinstance(event, GroupMessageEvent):
        success_list, fail_list = await unfollow_liver_list(event.group_id, uid_list, 1)
    await unfollow_liver_command.finish(f"取关成功:\n{success_list}\n取关失败:\n{fail_list}")

listFollowingCommand = on_command("查询关注", aliases={"查询成分"}, permission=ALL_PERMISSION)
@listFollowingCommand.handle()
async def listFollowingCommandHandler(event: Union[PrivateMessageEvent, GroupMessageEvent], args: Message = CommandArg()):
    await create_user(event)
    inputArgs = args.extract_plain_text().split()
    defaultArgs = ['直播', 'up主', '番剧']

    if isinstance(event, PrivateMessageEvent):
        user_id = event.sender.user_id
        user_type = 0
    elif isinstance(event, GroupMessageEvent):
        user_id = event.group_id
        user_type = 1
    
    exceptArgs = set(inputArgs) - set(defaultArgs)

    if len(exceptArgs) != 0:
        logger.info(f'{__PLUGIN_NAME}查询失败，存在错误参数: {exceptArgs}')
        await listFollowingCommand.finish(f"查询失败，存在错误参数:{exceptArgs}\n请正确输入命令,例如: '查询成分 直播' 或 '查询成分 直播 up主 番剧'")

    if not inputArgs:
            inputArgs = defaultArgs
    try:
        res = bili_database.query_info(user_type, user_id)
        if res:
            if user_type == 0:
                followed_up_list = bili_database.query_user_relation(1, user_id)
                followed_liver_list = bili_database.query_user_relation(3, user_id)
                followed_telegram_list = bili_database.query_user_relation(5, user_id)
            else:
                followed_up_list = bili_database.query_group_relation(1, user_id)
                followed_liver_list = bili_database.query_group_relation(3, user_id)
                followed_telegram_list = bili_database.query_group_relation(5, user_id)
            logger.debug(f'{__PLUGIN_NAME}\nup:{followed_up_list}\nliver:{followed_liver_list}\ntelegram{followed_telegram_list}')
            
            textMsg = ""
            if 'up主' in inputArgs:
                if followed_up_list:
                    textMsg += '关注的up主:\n'
                    for up_uid in followed_up_list:
                        up_uid, up_name, _ = bili_database.query_info(2, up_uid[0])
                        textMsg += '> ' + f"{up_name}(uid: {up_uid})" + '\n'
                        
                else:
                    textMsg += '无关注的up主\n'
            textMsg += '\n'

            if '直播' in inputArgs:
                if followed_liver_list:
                    textMsg += '关注的主播:\n'
                    for liver_uid in followed_liver_list:
                        liver_uid, liver_name, _, _ = bili_database.query_info(3, liver_uid[0])
                        textMsg += '> ' + f"{liver_name}(uid: {liver_uid})" + '\n'
                else:
                    textMsg += '无关注的主播\n'
            textMsg += '\n'

            if '番剧' in inputArgs:
                if followed_telegram_list:
                    textMsg += '关注的番剧\n'
                    for season_id in followed_telegram_list:
                        season_id, telegram_title, _ = bili_database.query_info(4, season_id[0])
                        textMsg += '> ' + f"{telegram_title}(season_id: ss{season_id})" + '\n'
                
                else:
                    textMsg += '无关注的番剧'
            textMsg += '\n'

            await listFollowingCommand.send(textMsg)
        else:
            await listFollowingCommand.finish("关注列表为空")
    except Exception as _:
        ex_type, ex_val, _ = sys.exc_info()
        exception_msg = f'【错误报告】\n查询关注时发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n'
        logger.error(f"{__PLUGIN_NAME}" + exception_msg + traceback.format_exc())
    await listFollowingCommand.finish()

followUpCommand = on_command("关注up", permission=ALL_PERMISSION)
@followUpCommand.handle()
async def followUpCommandHandler(event: Union[PrivateMessageEvent, GroupMessageEvent], args: Message = CommandArg()):
    await create_user(event)
    uid_list = args.extract_plain_text().split() 
    if isinstance(event, PrivateMessageEvent):
        success_list, fail_list = await follow_up_list(event.sender.user_id, uid_list, 0)
    if isinstance(event, GroupMessageEvent):
        success_list, fail_list = await follow_up_list(event.group_id, uid_list, 1)
    await followUpCommand.finish(f"关注成功:\n{success_list}\n关注失败:\n{fail_list}")

unfollowUpCommand = on_command("取关up", permission=ALL_PERMISSION)
@unfollowUpCommand.handle()
async def unfollowUpCommandHandler(event: Union[PrivateMessageEvent, GroupMessageEvent], args: Message = CommandArg()):
    await create_user(event)
    uid_list = args.extract_plain_text().split()
    if isinstance(event, PrivateMessageEvent):
        success_list, fail_list = await unfollow_up_list(event.sender.user_id, uid_list, 0)
    if isinstance(event, GroupMessageEvent):
        success_list, fail_list = await unfollow_up_list(event.group_id, uid_list, 1)
    await unfollowUpCommand.finish(f"取关成功:\n{success_list}\n取关失败:\n{fail_list}")

followTelegramCommand = on_command("关注番剧", permission=ALL_PERMISSION)
@followTelegramCommand.handle()
async def followTelegramCommandHandler(event: Union[PrivateMessageEvent, GroupMessageEvent], args: Message = CommandArg()):
    await create_user(event)
    tele_id_list = args.extract_plain_text().split()
    if isinstance(event, PrivateMessageEvent):
        success_list, fail_list = await follow_telegram_list(event.sender.user_id, tele_id_list, 0)
    if isinstance(event, GroupMessageEvent):
        success_list, fail_list = await follow_telegram_list(event.group_id, tele_id_list, 1)
    await followTelegramCommand.finish(f"关注成功:\n{success_list}\n关注失败:\n{fail_list}")

unfollowTelegramCommand = on_command("取关番剧", permission=ALL_PERMISSION)
@unfollowTelegramCommand.handle()
async def unfollowTelegramCommandHandler(event: Union[PrivateMessageEvent, GroupMessageEvent], args: Message = CommandArg()):
    await create_user(event)
    season_id_list = args.extract_plain_text().split()
    if isinstance(event, PrivateMessageEvent):
        success_list, fail_list = await unfollow_telegram_list(event.sender.user_id, season_id_list, 0)
    if isinstance(event, GroupMessageEvent):
        success_list, fail_list = await unfollow_telegram_list(event.group_id, season_id_list, 1)
    await unfollowTelegramCommand.finish(f"取关成功:\n{success_list}\n取关失败:\n{fail_list}")

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
    await create_user(event)
    sJson = event.get_message()[-1].get('data')
    data = json.loads(sJson['data'])
    uid = data['meta']['news']['jumpUrl'].split('?')[0].split('/')[-1]
    
    success_list, fail_list = await follow_up_list(event.sender.user_id, [uid], 0)
    
    if success_list:
        await followUpByShare.finish(f"关注up成功: <{success_list[0]}>")
    elif fail_list:
        await followUpByShare.finish(f"关注up失败: <{fail_list[0]}>")

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
    try:
        await create_user(event)
        sJson = event.get_message()[-1].get('data')
        data = json.loads(sJson['data'])
        roomNumber = data['meta']['news']['jumpUrl'].split('?')[0].split('/')[-1]

        uid, _ = await bili_client.init_liver_info_by_room_id(roomNumber)

        success_list, fail_list = await follow_liver_list(event, event.sender.user_id, [uid], 0)

        if success_list:
            await followUpByShare.finish(f"关注主播成功: <{success_list[0]}>")
        elif fail_list:
            await followUpByShare.finish(f"关注主播失败: <{fail_list[0]}> ")
        
    except nonebot.exception.FinishedException:
        pass
    except BiliInvalidRoomId:
        await followStreamerByShare.finish('关注失败: 无效的房间号')
    except Exception:
        ex_type, ex_val, _ = sys.exc_info()
        logger.error(f'{__PLUGIN_NAME}获取主播 <{uid}> 信息时发生错误')
        logger.error(f'{__PLUGIN_NAME}错误类型: {ex_type},错误值: {ex_val}')
        await followStreamerByShare.finish('关注失败: 连接错误')

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
    await create_user(event)
    sJson = event.get_message()[-1].get('data')
    data = json.loads(sJson['data'])
    epID = data['meta']['detail_1']['qqdocurl'].split('?')[0].split('/')[-1]
    
    success_list, fail_list = await follow_telegram_list(event.sender.user_id, [epID], 0)
    
    if success_list:
        await followUpByShare.finish(f"关注番剧成功: <{success_list[0]}>")
    elif fail_list:
        await followUpByShare.finish(f"关注番剧失败: <{fail_list[0]}> ")

follow_by_share_short_url = on_message(
    rule = regex('^\[CQ:json[\w\W]*"appid":100951776[\w\W]*b23.tv[\w\W]*') & privateMessageRule,
    permission=PRIVATE_FRIEND
)
@follow_by_share_short_url.handle()
async def short_url_handler(event: PrivateMessageEvent):
    try:
        await create_user(event)
        sJson = event.get_message()[-1].get('data')
        shortLink = re.search("https:\/\/b23.tv\/\w+", sJson['data'])
        short_url = shortLink.group()
        logger.debug(f"get short url = {short_url}")
        
        msg_type = 0
        user_id = event.sender.user_id
        id_type, target_uid = await bili_client.parse_short_url(short_url)
        #isSuccess, id_type, uid = await parseB23Url(short_url)
        if id_type == 0:
            success_list, fail_list = await follow_up_list(user_id, [target_uid], msg_type)
            if success_list:
                await follow_by_share_short_url.finish(f"关注成功: {success_list[0]}")
            elif fail_list:
                await follow_by_share_short_url.finish(f"关注失败: {fail_list[0]}")
            
        elif id_type == 1:
            liver_uid, _ = await bili_client.init_liver_info_by_room_id(target_uid)
            success_list, fail_list = await follow_liver_list(user_id, [liver_uid], msg_type)
            if success_list:
                await follow_by_share_short_url.finish(f"关注成功: {success_list[0]}")
            elif fail_list:
                await follow_by_share_short_url.finish(f"关注失败: {fail_list[0]}")

        elif id_type == 2:
            success_list, fail_list = await follow_telegram_list(user_id, [target_uid], msg_type)
            if success_list:
                await follow_by_share_short_url.finish(f"关注成功: {success_list[0]}")
                
            elif fail_list:           
                await follow_by_share_short_url.finish(f"关注失败: {fail_list[0]}")
        else:
            await follow_by_share_short_url.finish(f"关注失败: 非法短链接{short_url}")
    except nonebot.exception.FinishedException:
        pass
    except BiliInvalidShortUrl:
        await follow_by_share_short_url.finish('关注失败: 非法或不支持的短链接')
    except Exception as _:
        ex_type, ex_val, _ = sys.exc_info()
        logger.error(f'{__PLUGIN_NAME}【错误报告】\n解析短链接 <{short_url}> 时发生错误\n错误类型: {ex_type}\n错误值: {ex_val}\n{traceback.format_exc()}')
        await follow_by_share_short_url.finish('关注失败: 连接错误')

helpCommand = on_command("help", permission=ALL_PERMISSION, aliases={'帮助'})
@helpCommand.handle()
async def sendHelpMsg(event: MessageEvent):
    await create_user(event)
    helpMsg = ""
    with open(f'{PackagePath}/file/source/help.json', 'r', encoding='utf-8') as f:
        helpMsg = json.load(f)
    await helpCommand.finish(helpMsg)

publicBroacast = on_command("broacast", aliases={'广播'}, permission=permission.SUPERUSER)
@publicBroacast.handle()
async def sendBroacast(event: MessageEvent):
    announcement = ""
    announcementPath = f'{PackagePath}/file/source/announcement.json'
    if os.path.exists(announcementPath):
        with open(announcementPath, 'r', encoding='utf-8') as f:
            announcement = json.load(f)
            
        users = GetAllUser()
        await SendMsgToUsers(announcement, users)

        groups = GetAllGroup()
        await SendMsgToGroups(announcement, groups)

        await publicBroacast.finish("公告发送成功")
    else:
        logger.debug(f'{__PLUGIN_NAME}公告文件不存在')
        await publicBroacast.finish("公告发送失败: 公告文件不存在") 

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
logger.debug(f'{__PLUGIN_NAME}注册定时任务')
scheduler.add_job(check_bili_live, "interval", minutes=1, id="biliStream", misfire_grace_time=90)
scheduler.add_job(check_up_update, "interval", minutes=5, id="biliUp", misfire_grace_time=90)
scheduler.add_job(check_telegram_update, "interval", minutes=10, id="biliTele", misfire_grace_time=90)