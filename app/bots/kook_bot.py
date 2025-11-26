import asyncio
from khl import Bot

def create_kook_bot(token, config=None):
    bot = Bot(token=token)
    print("KOOK机器人已创建，准备设置命令...")
    return setup_kook_bot(bot)

def setup_kook_bot(bot: Bot):
    async def on_startup():
        print('KOOK机器人已成功启动！')
        print('------')
        print('【KOOK可用文本命令】:')

    @bot.task.add_interval(minutes=30)
    async def register_slash_task():
        print('  .ping - 测试机器人是否在线')
        print('  .hello - 问候命令')
        print('------')

    bot.on_startup = on_startup
    return bot
