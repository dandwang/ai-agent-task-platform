import logging
import sys


def configure_logging(log_level: str) -> None:
    """配置结构简洁、适合本地学习的标准输出日志。"""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
        force=True,
    )
