import requests
from typing import Optional, Dict
from app.config.settings import get_settings

class DeepseekClient:
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.DEEPSEEK_API_KEY
        self.endpoint = self.settings.DEEPSEEK_ENDPOINT
        self.model = self.settings.DEEPSEEK_MODEL

        # 初始化日志
        if self.available():
            print(f'[Deepseek] ✅ 初始化成功 - 模型: {self.model}, 端点: {self.endpoint}')
        else:
            print('[Deepseek] ❌ 初始化失败 - API密钥未配置')

    def available(self) -> bool:
        return bool(self.api_key)

    def extract_trade(self, text: str) -> Optional[Dict]:
        if not self.available():
            return None
        
        # 记录输入文本
        print(f'[Deepseek] 📥 收到解析请求，文本长度: {len(text)} 字符')
        print(f'[Deepseek] 📝 输入文本内容: {text[:500]}{"..." if len(text) > 500 else ""}')
        
        prompt = (
            "你是专业的交易文本解析助手。请从中文交易信号或战报中提取结构化字段。\n\n"
            "⚠️ 重要判断规则：\n"
            "1. 如果文本只是总结、反思、道歉、愿景、策略说明等非交易信号内容，返回: {}\n"
            "2. 如果文本提到\"取消\"、\"休息\"、\"波动小\"、\"无法开单\"等非交易信息，返回: {}\n"
            "3. 如果文本包含具体的交易对、价格、方向、止盈止损等交易信号，才进行提取\n"
            "4. 如果文本是回复/引用之前的消息，且包含止盈/止损/出局信息，必须提取\n"
            "5. 如果文本包含\"出局\"、\"部分出局\"、\"出局XX%\"、\"剩余\"、\"继续持有\"、\"设置止损\"等关键词，必须识别为更新信号\n"
            "6. 如果文本中出现「合约策略（限价）」、「具体产品」、「进行方向」、「进场点位」、「止损点位」、「止盈点位」等字段，且给出了具体价格，一定要解析为入场信号（type=\"entry\"）。\n"
            "7. 如果文本中出现「补仓」、「补货」、「加仓」等字样，一定要识别为更新信号（type=\"update\"），并在 status 字段中体现，例如: \"补仓\"、\"补货\"、\"加仓\"。\n\n"
            "只返回纯JSON格式，不要包含任何markdown代码块、解释文字或其他内容。\n\n"
            "如果是入场信号（包含交易对、进场价、止盈、止损），输出JSON格式: {\n"
            "  \"type\": \"entry\",\n"
            "  \"symbol\": \"交易对名称（如BTC-USDT-SWAP，如果文本中提到比特币/BTC则使用BTC-USDT-SWAP，提到以太坊/ETH则使用ETH-USDT-SWAP）\",\n"
            "  \"side\": \"long\" 或 \"short\"（做多或做空，空单/做空/卖出=short，多单/做多/买入=long），\n"
            "  \"entry_price\": 进场价格（数字，从文本中提取，如\"现价87400附近\"则提取87400，\"现价2806附近\"则提取2806，\"2806附近\"则提取2806），\n"
            "  \"take_profit\": 止盈价格（数字，从文本中提取，如\"止盈:2650\"则提取2650，\"止盈2650\"则提取2650），\n"
            "  \"stop_loss\": 止损价格（数字，从文本中提取，如\"止损:2870\"则提取2870，\"止损2870\"则提取2870）\n"
            "}\n\n"
            "📝 解析示例：\n"
            "示例1: \"以太坊现价2806附近做空\\n\\n止盈:2650\\n\\n止损:2870\\n\\n轻仓介入！！！\"\n"
            "应解析为: {\"type\":\"entry\",\"symbol\":\"ETH-USDT-SWAP\",\"side\":\"short\",\"entry_price\":2806,\"take_profit\":2650,\"stop_loss\":2870}\n\n"
            "示例2: \"BTC现价87400附近做多 止盈90000 止损86000\"\n"
            "应解析为: {\"type\":\"entry\",\"symbol\":\"BTC-USDT-SWAP\",\"side\":\"long\",\"entry_price\":87400,\"take_profit\":90000,\"stop_loss\":86000}\n\n"
            "示例3: \"eth 1800 多单 止盈：4900，止损1600\"\n"
            "应解析为: {\"type\":\"entry\",\"symbol\":\"ETH-USDT-SWAP\",\"side\":\"long\",\"entry_price\":1800,\"take_profit\":4900,\"stop_loss\":1600}\n\n"
            "示例4: \"合约策略（限价）\\n\\n具体产品：BTC\\n\\n进行方向：做多\\n\\n进场点位：91530\\n\\n止损点位：89710\\n\\n止盈点位：96216\"\n"
            "应解析为: {\"type\":\"entry\",\"symbol\":\"BTC-USDT-SWAP\",\"side\":\"long\",\"entry_price\":91530,\"take_profit\":96216,\"stop_loss\":89710}\n\n"
            "如果是出场/止盈/止损/全部出局/部分出局更新（包含以下任一关键词：出局、止盈、止损、获利、亏损、部分出局、出局XX%、剩余、继续持有、设置止损、成本价等），输出JSON格式: {\n"
            "  \"type\": \"update\",\n"
            "  \"status\": \"已止盈\"|\"已止损\"|\"带单主动止盈\"|\"带单主动止损\"|\"部分止盈\"|\"部分止损\"|\"部分出局\"|\"浮盈\"|\"浮亏\",\n"
            "  \"pnl_points\": 盈亏点数（数字，如\"获利1400点\"则提取1400，\"亏损500点\"则提取-500。如果是部分出局，根据出局价格和进场价计算，例如：空单进场价92550，出局价90300，则盈亏为92550-90300=2250点）\n"
            "}\n\n"
            "⚠️ 特别注意（这些情况必须识别为更新信号）：\n"
            "- \"出局XX%\"（如\"出局70%\"、\"出局50%\"）→ status: \"部分止盈\"或\"部分出局\"\n"
            "- \"部分出局\"、\"部分止盈\"、\"部分止损\"→ status: 对应状态\n"
            "- \"剩余部分继续持有\"、\"剩下部分\"、\"剩余XX%\"→ status: \"部分止盈\"或\"部分出局\"\n"
            "- \"设置成本价XX止损\"、\"设置止损\"、\"止损调整为XX\"→ status: \"浮盈\"或\"浮亏\"（表示更新止损）\n"
            "- \"现价XX出局\"、\"XX价格出局\"→ status: \"已止盈\"或\"已止损\"（根据盈亏判断）\n"
            "- \"补仓\"、\"补货\"、\"加仓\"→ 一律识别为更新信号（type: \"update\"），在 status 中体现（例如: \"补仓\"），如果可以的话，也在额外字段中说明补仓价格和次数。\n"
            "- 即使消息没有明确提到交易对，只要包含上述关键词和价格信息，也要识别为更新信号\n\n"
            "若文本只是总结、反思、道歉、策略说明、取消交易等非交易信号内容，返回: {}\n\n"
            "只返回JSON，不要有任何其他文字、markdown标记或解释。"
        )
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ]
        }
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            
            # 验证端点URL
            if not self.endpoint or not self.endpoint.startswith('http'):
                print(f'[Deepseek] ❌ API端点配置错误: {self.endpoint}')
                return None
            
            # 确保端点完整（如果只配置了基础URL，自动补全）
            if self.endpoint.endswith('/') and not self.endpoint.endswith('/completions'):
                self.endpoint = self.endpoint.rstrip('/') + '/v1/chat/completions'
                print(f'[Deepseek] ⚠️ 自动补全端点URL: {self.endpoint}')
            
            print(f'[Deepseek] 🚀 发送API请求到: {self.endpoint}')
            print(f'[Deepseek] 📤 请求体大小: {len(str(body))} 字符')
            
            r = requests.post(self.endpoint, json=body, headers=headers, timeout=30)
            
            print(f'[Deepseek] 📥 API响应状态码: {r.status_code}')
            
            if r.status_code != 200:
                print(f'[Deepseek] ❌ API请求失败: {r.status_code}')
                print(f'[Deepseek] ❌ 端点: {self.endpoint}')
                print(f'[Deepseek] ❌ 响应内容前500字符: {r.text[:500]}')
                # 如果返回的是HTML，说明端点可能不对
                if r.text.strip().startswith('<!DOCTYPE') or r.text.strip().startswith('<html'):
                    print(f'[Deepseek] ⚠️ API返回了HTML而不是JSON，请检查端点配置是否正确')
                    print(f'[Deepseek] ⚠️ 当前端点: {self.endpoint}')
                    print(f'[Deepseek] ⚠️ 正确的端点应该是类似: https://api.v3.cm/v1/chat/completions')
                return None
            
            # 检查响应是否为JSON
            try:
                data = r.json()
            except ValueError as e:
                print(f'[Deepseek] ❌ API返回的不是JSON格式: {e}')
                print(f'[Deepseek] ❌ 响应内容: {r.text[:500]}')
                return None
            
            # 检查响应结构
            if "choices" not in data or not data.get("choices"):
                print(f'[Deepseek] ⚠️ API响应格式异常，缺少choices字段')
                print(f'[Deepseek] ⚠️ 响应内容: {data}')
                return None
            
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # 记录 API 响应的完整内容（用于调试）
            print(f'[Deepseek] 📥 API返回的完整响应: {str(data)[:1000]}{"..." if len(str(data)) > 1000 else ""}')
            print(f'[Deepseek] 📝 API返回的原始内容: {content[:500]}{"..." if len(content) > 500 else ""}')
            
            # 如果content为空，返回空结果
            if not content or not content.strip():
                print(f'[Deepseek] ⚠️ API返回的内容为空')
                return {}
            
            import json
            import re
            
            # 清理内容：移除可能的markdown代码块标记
            content = content.strip()
            # 移除 ```json 和 ``` 标记
            content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
            content = re.sub(r'^```\s*', '', content, flags=re.MULTILINE)
            content = re.sub(r'```\s*$', '', content, flags=re.MULTILINE)
            content = content.strip()
            
            # 尝试提取JSON对象（如果内容中包含其他文字）
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                print(f'[Deepseek] ⚠️ JSON解析失败')
                print(f'[Deepseek] ⚠️ 原始内容长度: {len(content)}')
                print(f'[Deepseek] ⚠️ 原始内容前500字符: {content[:500]}')
                print(f'[Deepseek] ⚠️ 解析错误: {e}')
                
                # 如果内容为空或只有空白，返回空结果
                if not content.strip():
                    print(f'[Deepseek] ⚠️ 内容为空，返回空结果')
                    return {}
                
                # 尝试提取JSON对象（如果内容中包含其他文字）
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                    print(f'[Deepseek] 🔍 提取到JSON片段: {content[:200]}')
                
                # 尝试修复常见的JSON格式问题
                fixed_content = content.replace("'", '"')  # 单引号转双引号
                # 修复未加引号的键名（但保留已加引号的）
                fixed_content = re.sub(r'(\w+):', lambda m: f'"{m.group(1)}":' if not m.group(1).startswith('"') else m.group(0), fixed_content)
                try:
                    result = json.loads(fixed_content)
                    print(f'[Deepseek] ✅ 修复后成功解析JSON')
                except Exception as e2:
                    print(f'[Deepseek] ❌ 修复后仍无法解析: {e2}')
                    print(f'[Deepseek] ❌ 修复后的内容: {fixed_content[:500]}')
                    # 如果无法解析，返回空结果而不是None
                    result = {}
            
            if result and isinstance(result, dict) and result.get('type'):
                # 详细日志：显示进出场点位、止盈止损情况
                if result.get('type') == 'entry':
                    symbol = result.get('symbol', 'N/A')
                    side = result.get('side', 'N/A')
                    entry = result.get('entry_price', 'N/A')
                    tp = result.get('take_profit', 'N/A')
                    sl = result.get('stop_loss', 'N/A')
                    log_msg = f'[Deepseek] ✅ 提取到入场信号\n  📊 交易对: {symbol} | 方向: {side.upper()}\n  📍 进场点位: {entry}\n  🎯 止盈点位: {tp}\n  🛑 止损点位: {sl}'
                    print(log_msg)
                    # 同时写入日志文件（如果 MonitorCog 的 logger 已初始化）
                    try:
                        import logging
                        logger = logging.getLogger('monitor')
                        if logger.handlers:
                            logger.info(log_msg)
                    except:
                        pass
                elif result.get('type') == 'update':
                    status = result.get('status', 'N/A')
                    pnl = result.get('pnl_points', 'N/A')
                    log_msg = f'[Deepseek] ✅ 提取到更新信号\n  📈 状态: {status}'
                    if pnl != 'N/A':
                        log_msg += f'\n  💰 盈亏点数: {pnl}'
                    print(log_msg)
                    # 同时写入日志文件
                    try:
                        import logging
                        logger = logging.getLogger('monitor')
                        if logger.handlers:
                            logger.info(log_msg)
                    except:
                        pass
            return result
        except Exception as e:
            error_msg = f'[Deepseek] ❌ 提取异常: {e}'
            print(error_msg)
            import traceback
            tb_str = traceback.format_exc()
            print(tb_str)
            # 同时写入日志文件
            try:
                import logging
                logger = logging.getLogger('monitor')
                if logger.handlers:
                    logger.error(f'{error_msg}\n{tb_str}')
            except:
                pass
            return None
