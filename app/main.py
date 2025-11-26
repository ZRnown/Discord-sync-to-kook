import threading
from app.config.settings import get_settings
from app.bots.discord_bot import create_discord_bot, setup_discord_bot
from app.bots.kook_bot import create_kook_bot

# 全局实例
kook_bot_instance = None

def run_discord_bot(kook_bot=None):
    import os
    import asyncio
    settings = get_settings()
    token = settings.DISCORD_BOT_TOKEN
    if token:
        bot = create_discord_bot(token)
        if kook_bot:
            setup_discord_bot(bot, token, kook_bot)
        else:
            setup_discord_bot(bot, token)
        try:
            print('[Discord] 正在启动...')
            bot.run(token)
        except Exception as e:
            print(f'[Discord] 启动异常: {e}')

def run_kook_bot():
    import asyncio
    settings = get_settings()
    async def start_kook():
        token = settings.KOOK_BOT_TOKEN
        if token:
            bot = create_kook_bot(token)
            global kook_bot_instance
            kook_bot_instance = bot
            try:
                print('[KOOK] 正在启动...')
                await bot.start()
            except Exception as e:
                print(f'[KOOK] 启动异常: {e}')
    asyncio.run(start_kook())

def main():
    settings = get_settings()
    print('=== 多平台机器人启动器（带转发功能）===')

    threads = []
    if settings.ENABLE_KOOK and settings.KOOK_BOT_TOKEN:
        kt = threading.Thread(target=run_kook_bot, daemon=True)
        kt.start()
        threads.append(kt)
        import time; time.sleep(3)

    if settings.ENABLE_DISCORD and settings.DISCORD_BOT_TOKEN:
        dt = threading.Thread(target=lambda: run_discord_bot(kook_bot_instance), daemon=True)
        dt.start()
        threads.append(dt)

    print('所有机器人已启动，按Ctrl+C退出...')
    try:
        while True:
            alive = [t for t in threads if t.is_alive()]
            if not alive:
                break
            import time; time.sleep(1)
    except KeyboardInterrupt:
        print('退出')

if __name__ == '__main__':
    main()
