import re
from typing import List


def normalize_word(word: str) -> str:
    """标准化单词：保留字母、连字符、撇号，转小写"""
    if word is None:
        return ""
    text = str(word).strip()
    text = re.sub(r"[^A-Za-z\-']+", " ", text).strip().lower()
    return text


def natural_sort_key(s: str):
    """自然排序键：数字按数值排序"""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

