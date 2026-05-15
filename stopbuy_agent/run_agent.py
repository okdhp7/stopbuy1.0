"""
StopBuy AI Agent - 실행 엔트리포인트
"""
import asyncio
import sys
import os

# 경로 추가
sys.path.insert(0, os.path.dirname(__file__))

from agent.server import main

if __name__ == "__main__":
    asyncio.run(main())
