"""
app/utils/parser.py
Robust JSON extractor + repair for LLM outputs (Groq-safe)
"""

import json
import re
import logging

logger = logging.getLogger(__name__)


def extract_json(raw: str, expect=None, llm=None):
    text = raw.strip()

    # 1. Strip markdown fences
    m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if m:
        text = m.group(1).strip()

    # 2. Extract first balanced JSON object/array
    for open_c, close_c in [('{', '}'), ('[', ']')]:
        start = text.find(open_c)
        if start == -1:
            continue

        depth, in_str, esc = 0, False, False
        for i, ch in enumerate(text[start:], start):
            if esc:
                esc = False
                continue
            if ch == '\\' and in_str:
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue

            if ch == open_c:
                depth += 1
            elif ch == close_c:
                depth -= 1
                if depth == 0:
                    text = text[start:i + 1]
                    break
        else:
            # truncated JSON → take what we have
            text = text[start:]
        break

    # 3. 🔥 Fix common LLM JSON issues

    # Fix missing commas between strings in arrays
    text = re.sub(r'"\s+"', '", "', text)

    # Fix missing commas between key-value pairs
    text = re.sub(r'(":\s*"[^"]+")\s+(")', r'\1, \2', text)

    # 4. Remove trailing commas
    text = re.sub(r',\s*([}\]])', r'\1', text)

    # 5. Close unclosed quotes
    if len(re.findall(r'(?<!\\)"', text)) % 2 != 0:
        text += '"'

    # 6. Close unclosed braces/brackets
    opens  = text.count('{') - text.count('}')
    aopens = text.count('[') - text.count(']')
    text = text.rstrip().rstrip(',')

    text += ']' * aopens + '}' * opens

    # 7. Try parsing
    try:
        data = json.loads(text)

        if expect and not isinstance(data, expect):
            raise ValueError(f"Expected {expect}, got {type(data)}")

        return data

    except Exception as e:
        logger.warning(f"Initial JSON parse failed: {e}")

        # 8. 🚀 OPTIONAL: LLM repair fallback
        if llm:
            try:
                repair_prompt = f"""
Fix this JSON. Return ONLY valid JSON. Do not add explanation.

{text}
"""
                repaired = llm.invoke(repair_prompt).content.strip()

                data = json.loads(repaired)

                if expect and not isinstance(data, expect):
                    raise ValueError(f"Expected {expect}, got {type(data)}")

                logger.info("JSON repaired successfully via LLM")
                return data

            except Exception as repair_error:
                logger.error(f"LLM JSON repair failed: {repair_error}")

        raise ValueError(f"JSON parsing failed: {e}\n\nRaw:\n{raw[:500]}")