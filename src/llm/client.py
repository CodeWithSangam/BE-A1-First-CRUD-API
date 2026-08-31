import os
import time
import random
import logging
from openai import OpenAI, APITimeoutError, RateLimitError, APIStatusError

logger = logging.getLogger(__name__)

def make_client():
    return OpenAI(
        base_url=os.getenv("LLM_BASE_URL"),
        api_key=os.getenv("LLM_API_KEY"),
        timeout=30.0,
        max_retries=0  # hum khud handle karenge
    )

def call_with_retry(messages: list, model: str, temperature: float = 0.2) -> tuple[str, dict]:
    """
    Model call karo with retry on timeout/429/5xx.
    Returns: (raw_text, cost_info)
    """
    client = make_client()
    max_attempts = 3
    delays = [1, 2, 4]

    for attempt in range(max_attempts):
        start = time.time()
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=messages
            )
            duration = int((time.time() - start) * 1000)
            raw = response.choices[0].message.content
            cost_info = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "duration_ms": duration,
                "model": model
            }
            logger.info(f"LLM call success | {cost_info}")
            return raw, cost_info

        except APITimeoutError:
            if attempt < max_attempts - 1:
                delay = delays[attempt] + random.uniform(0, 1)
                time.sleep(delay)
                continue
            raise

        except RateLimitError:
            if attempt < max_attempts - 1:
                delay = delays[attempt] + random.uniform(0, 1)
                time.sleep(delay)
                continue
            raise
        except APIStatusError as e:
        # 4xx pe kabhi retry mat karo
            if e.status_code < 500:
                raise
        # 5xx pe retry
            if attempt < max_attempts - 1:
                delay = delays[attempt] + random.uniform(0, 1)
                time.sleep(delay)
                continue
            raise