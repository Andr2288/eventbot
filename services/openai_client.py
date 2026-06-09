"""Спільний клієнт OpenAI API."""

from openai import AsyncOpenAI

from utils.env import require


def get_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=require("OPENAI_API_KEY"))
