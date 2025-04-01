# -*- coding: utf-8 -*-
import base64
import json

import requests

from pkg.plugin.context import register, handler, llm_func, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *  # 导入事件类
import pkg.platform.types as platform_types


# 注册插件
@register(name="Hello", description="hello world", version="0.1", author="RockChinQ")
class MyPlugin(BasePlugin):

    # 插件加载时触发
    def __init__(self, host: APIHost):
        pass

    # 异步初始化
    async def initialize(self):
        pass

    async def get_local_search_url(self, query, num_results=10, searx_host="http://124.223.45.165:22109"):
        url = f"{searx_host}/search"
        params = {
            "q": query,
            "categories": "images",
            "num": num_results,
            "format": "json"
        }
        import os
        import shutil
        import aiohttp  # 引入 aiohttp 库用于异步请求

        # 创建img_download目录
        download_dir = os.path.join(os.path.dirname(__file__), 'img_download')
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        try:
            print('start query keyword:', query)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()  # 检查是否有 HTTP 错误
                    results = await response.json()  # 异步解析 JSON
                    img = {}
                    for it in results['results']:
                        if 'resolution' in it and 'img_src' in it:
                            print(it['resolution'], it['source'], it['title'], it['img_src'])
                            parts = it['resolution'].split('x')
                            if not len(parts) == 2:
                                continue
                            img_url = it['img_src']
                            try:
                                # 异步下载图片
                                async with session.get(img_url) as img_response:
                                    img_response.raise_for_status()
                                    img_filename = os.path.join(download_dir, os.path.basename(img_url))
                                    with open(img_filename, 'wb') as out_file:
                                        out_file.write(await img_response.read())  # 异步读取图片内容
                                    img = {'url': img_url, 'width': int(parts[0]), 'height': int(parts[1]),
                                           'local_path': img_filename}
                                    await self.host.send_active_message('person', 'ou_63053bc6508a9fc06be536d937b50e4e',
                                                                        [platform_types.Image(id=img_filename,
                                                                                              path=img_filename,
                                                                                              url=img_url)])
                                    # with open(img_filename, 'rb') as img_file:
                                    #     img['base64'] = base64.b64encode(img_file.read()).decode('utf-8')
                            except aiohttp.ClientError as e:
                                print(f"下载图片 {img_url} 失败: {e}")
                                continue
                            print(f'{query} :{img}')
                            return img
                        else:
                            print(f"未找到与查询 '{query}' 相关的图片结果。")
                            return None
        except aiohttp.ClientError as e:
            print(f"搜索查询 '{query}' 失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"解析 JSON 响应失败: {e}, 响应内容：{await response.text()}")
            return None
        except KeyError as e:
            print(f"KeyError: 缺少预期的键: {e}, 响应内容：{await response.text()}")
            return None

    # 当收到个人消息时触发
    @handler(PersonNormalMessageReceived)
    async def person_normal_message_received(self, ctx: EventContext):
        msg = ctx.event.text_message  # 这里的 event 即为 PersonNormalMessageReceived 的对象
        print('plugin handle:', msg)
        if msg == "hello":  # 如果消息为hello

            # 输出调试信息
            self.ap.logger.debug("hello, {}".format(ctx.event.sender_id))

            # 回复消息 "hello, <发送者id>!"
            ctx.add_return("reply", ["hello, {}!".format(ctx.event.sender_id)])
            ctx.prevent_default()
        elif msg.startswith(("search", "搜", "搜索", "查询")):
            ctx.add_return("reply", ["等我找一找，待会儿回复你!"])
            keyword = msg
            # 截取关键字
            for keyword_prefix in ("search", "搜", "搜索", "查询"):
                if msg.startswith(keyword_prefix):
                    keyword = msg[len(keyword_prefix):].strip()
                    break
            ctx.prevent_default()
            # 调用搜索函数
            await self.get_local_search_url(keyword)
            # img = await self.get_local_search_url(keyword)
            # if img:
            #     # ctx.add_return("reply", [platform_types.Image(url=f'data:base64,{img["base64"]}')])
            #     print('add pic from:', img['local_path'], ':', img["url"])
            #     # ctx.add_return("reply", [platform_types.Image(url=img["url"])])
            #     ctx.add_return("reply", [platform_types.Image(id=img["img_filename"], path=img["local_path"], url=img["url"])])
            # 阻止该事件默认行为（向接口获取回复）


    # 当收到群消息时触发
    @handler(GroupNormalMessageReceived)
    async def group_normal_message_received(self, ctx: EventContext):
        msg = ctx.event.text_message  # 这里的 event 即为 GroupNormalMessageReceived 的对象
        if msg == "hello":  # 如果消息为hello

            # 输出调试信息
            self.ap.logger.debug("hello, {}".format(ctx.event.sender_id))

            # 回复消息 "hello, everyone!"
            ctx.add_return("reply", ["hello, everyone!"])

            # 阻止该事件默认行为（向接口获取回复）
            ctx.prevent_default()

    # 插件卸载时触发
    def __del__(self):
        pass
