import json
from typing import List, Dict, Any, AsyncGenerator
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import httpx
import asyncio

from core.config import APIKEY_PATH
from core.logger import get_logger
from core.ip_tracker import track_ip

router = APIRouter()
logger = get_logger(__name__)

# AI接口配置
AI_TIMEOUT = 30.0  # 超时时间：30秒
AI_MAX_RETRIES = 3  # 最大重试次数：3次


def _load_api_keys_raw() -> List[str]:
    """加载原始 API 密钥"""
    try:
        with open(APIKEY_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and isinstance(data.get("keys"), list):
            return [str(x) for x in data.get("keys")]
        elif isinstance(data, list):
            return [str(x) for x in data]
        else:
            return []
    except Exception:
        return []


def _load_api_keys_masked() -> List[Dict[str, Any]]:
    """加载并打码 API 密钥"""
    raw_keys = _load_api_keys_raw()
    keys = []
    for idx, k in enumerate(raw_keys):
        if not k:
            masked = ""
        elif len(k) <= 6:
            masked = "***"
        else:
            masked = k[:3] + "***" + k[-3:]
        keys.append({"index": idx, "label": f"key{idx+1}", "masked": masked})
    return keys


def _get_api_key_from_payload(payload: dict) -> str:
    """从payload中获取API密钥（支持预置密钥）"""
    api_key = (payload.get("api_key") or "").strip()
    key_index = payload.get("key_index", None)
    
    # 如果提供了 key_index，优先使用预置密钥
    if (not api_key) and key_index is not None:
        try:
            idx = int(key_index)
            raw_keys = _load_api_keys_raw()
            if 0 <= idx < len(raw_keys):
                api_key = raw_keys[idx]
        except Exception:
            pass
    
    return api_key


async def _call_ai_with_retry(url: str, payload: dict, headers: dict, max_retries: int = AI_MAX_RETRIES) -> dict:
    """
    带重试机制的AI API调用
    
    参数：
    - url: API地址
    - payload: 请求体
    - headers: 请求头
    - max_retries: 最大重试次数
    
    返回：
    - API响应数据
    
    异常：
    - HTTPException: 请求失败
    """
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"AI请求尝试 {attempt}/{max_retries}")
            
            async with httpx.AsyncClient(timeout=AI_TIMEOUT) as client:
                r = await client.post(url, json=payload, headers=headers)
                r.raise_for_status()
                result = r.json()
                
                logger.info(f"AI请求成功 (尝试 {attempt}/{max_retries})")
                return result
                
        except httpx.TimeoutException as e:
            last_error = f"请求超时（{AI_TIMEOUT}秒）"
            logger.warning(f"AI请求超时 (尝试 {attempt}/{max_retries}): {e}")
            
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            last_error = f"HTTP {status_code}"
            logger.warning(f"AI请求失败 HTTP {status_code} (尝试 {attempt}/{max_retries})")
            
            # 4xx错误不重试（客户端错误）
            if 400 <= status_code < 500:
                raise HTTPException(status_code=502, detail=f"AI API错误: HTTP {status_code}")
                
        except Exception as e:
            last_error = str(e)
            logger.warning(f"AI请求异常 (尝试 {attempt}/{max_retries}): {e}")
        
        # 如果不是最后一次尝试，等待后重试
        if attempt < max_retries:
            wait_time = attempt * 1  # 递增等待：1秒、2秒、3秒
            logger.info(f"等待 {wait_time}秒 后重试...")
            await asyncio.sleep(wait_time)
    
    # 所有重试都失败
    logger.error(f"AI请求失败，已重试 {max_retries} 次: {last_error}")
    raise HTTPException(
        status_code=503, 
        detail=f"AI服务繁忙，请稍后再试（已重试{max_retries}次）"
    )


@router.get("/api/ai/keys")
async def api_ai_keys():
    """获取 API 密钥列表（打码）"""
    keys = _load_api_keys_masked()
    return {"count": len(keys), "keys": keys}


@router.post("/api/ai/chat")
async def api_ai_chat(payload: dict, request: Request):
    """
    AI 聊天接口（普通模式，等待完整回复）
    
    带重试机制：
    - 超时时间：30秒
    - 最大重试：3次
    - 失败提示："AI服务繁忙，请稍后再试"
    """
    # 获取并验证参数
    api_key = _get_api_key_from_payload(payload)
    content = (payload.get("content") or "").strip()
    model = (payload.get("model") or "Qwen/QwQ-32B").strip()
    system = (payload.get("system") or "").strip()
    
    if not api_key:
        logger.warning("AI请求失败：缺少API密钥")
        raise HTTPException(status_code=400, detail="missing api_key")
    if not content:
        logger.warning("AI请求失败：缺少内容")
        raise HTTPException(status_code=400, detail="missing content")
    
    logger.info(f"AI聊天请求 - 模型: {model}, 内容长度: {len(content)}")
    
    url = "https://api.siliconflow.cn/v1/chat/completions"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": content})
    
    request_payload = {
        "model": model,
        "messages": messages,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # 使用带重试机制的调用
    try:
        result = await _call_ai_with_retry(url, request_payload, headers)
        
        # 提取回复内容
        msg = None
        try:
            msg = result.get("choices", [{}])[0].get("message", {}).get("content", None)
        except Exception:
            msg = None
        
        cleaned = "" if msg is None else str(msg).lstrip("\r\n")
        logger.info(f"AI聊天成功 - 回复长度: {len(cleaned)}")
        
        # 记录AI对话（为了用户隐私，不记录任何对话内容）
        try:
            await track_ip(request, "AI对话", {})
        except Exception as e:
            logger.warning(f"记录AI对话失败: {e}")
        
        return {
            "message": cleaned,
            "raw": result,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"AI聊天异常: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/ai/chat/stream")
async def api_ai_chat_stream(payload: dict, request: Request):
    """
    AI 聊天接口（流式响应，像ChatGPT那样逐字显示）
    
    配置：
    - 超时时间：90秒（流式响应需要更长时间）
    - 逐字输出，实时显示
    """
    # 获取并验证参数
    api_key = _get_api_key_from_payload(payload)
    content = (payload.get("content") or "").strip()
    model = (payload.get("model") or "Qwen/QwQ-32B").strip()
    system = (payload.get("system") or "").strip()
    
    if not api_key:
        logger.warning("AI流式请求失败：缺少API密钥")
        raise HTTPException(status_code=400, detail="missing api_key")
    if not content:
        logger.warning("AI流式请求失败：缺少内容")
        raise HTTPException(status_code=400, detail="missing content")
    
    logger.info(f"AI流式聊天请求 - 模型: {model}, 内容长度: {len(content)}")
    
    # 记录AI对话（为了用户隐私，不记录任何对话内容）
    try:
        await track_ip(request, "AI对话", {})
    except Exception as e:
        logger.warning(f"记录AI对话失败: {e}")
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        """生成流式响应"""
        url = "https://api.siliconflow.cn/v1/chat/completions"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": content})
        
        request_payload = {
            "model": model,
            "messages": messages,
            "stream": True,  # 关键：启用流式响应
            "max_tokens": 4096,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        total_chars = 0
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:  # 流式响应超时90秒
                async with client.stream("POST", url, json=request_payload, headers=headers) as response:
                    response.raise_for_status()
                    
                    # 逐行读取SSE数据
                    buffer = ""
                    async for chunk in response.aiter_bytes():
                        buffer += chunk.decode('utf-8')
                        
                        # 按行分割处理
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            
                            if not line:
                                continue
                            
                            # SSE格式：data: {...}
                            if line.startswith("data: "):
                                data_str = line[6:]  # 去掉 "data: " 前缀
                                
                                # 结束标志
                                if data_str.strip() == "[DONE]":
                                    break
                                
                                try:
                                    data = json.loads(data_str)
                                    delta = data.get("choices", [{}])[0].get("delta", {})
                                    content_chunk = delta.get("content", "")
                                    
                                    if content_chunk:
                                        total_chars += len(content_chunk)
                                        # 返回每个字符块，前端会逐字显示
                                        yield f"data: {json.dumps({'content': content_chunk}, ensure_ascii=False)}\n\n"
                                except json.JSONDecodeError:
                                    continue
                    
                    # 流结束标志
                    logger.info(f"AI流式聊天成功 - 总字符数: {total_chars}")
                    yield "data: [DONE]\n\n"
                    
        except httpx.TimeoutException as e:
            logger.error(f"AI流式请求超时: {e}")
            error_msg = json.dumps({"error": "AI服务繁忙，请稍后再试（请求超时）"}, ensure_ascii=False)
            yield f"data: {error_msg}\n\n"
        except httpx.HTTPStatusError as http_err:
            status_code = http_err.response.status_code
            logger.error(f"AI流式请求失败 HTTP {status_code}")
            error_msg = json.dumps({"error": f"AI服务繁忙，请稍后再试（HTTP {status_code}）"}, ensure_ascii=False)
            yield f"data: {error_msg}\n\n"
        except Exception as exc:
            logger.error(f"AI流式请求异常: {exc}", exc_info=True)
            error_msg = json.dumps({"error": "AI服务繁忙，请稍后再试"}, ensure_ascii=False)
            yield f"data: {error_msg}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用nginx缓冲
        }
    )

