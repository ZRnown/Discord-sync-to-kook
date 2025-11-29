import threading
from app.config.settings import get_settings
from app.bots.discord_bot import create_discord_bot, setup_discord_bot

def run_discord_bot():
    settings = get_settings()
    token = settings.DISCORD_BOT_TOKEN
    if token:
        bot = create_discord_bot(token)
        setup_discord_bot(bot, token)
        try:
            print('[Discord] 正在启动...')
            bot.run(token)
        except Exception as e:
            print(f'[Discord] 启动异常: {e}')

def main():
    settings = get_settings()
    print('=== Discord 机器人启动器 ===')

    if settings.ENABLE_DISCORD and settings.DISCORD_BOT_TOKEN:
        dt = threading.Thread(target=run_discord_bot, daemon=True)
        dt.start()

        print('Discord 机器人已启动，按Ctrl+C退出...')
    try:
            while dt.is_alive():
                import time
                time.sleep(1)
    except KeyboardInterrupt:
        print('退出')
    else:
        print('错误: DISCORD_BOT_TOKEN 未配置')

if __name__ == '__main__':
    main()
