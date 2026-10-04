import logging
import logging.handlers
import os
import sys
import yaml


DEFAULT_LOG_DIR = "/app/jic_competiion/log" # 默认日志目录
CONFIG_PATH = "/app/jic_competiion/config/log_config.yaml"

def get_log_dir():
    log_dir = DEFAULT_LOG_DIR
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = yaml.safe_load(f)
                if config and 'log_dir' in config:
                    log_dir = config['log_dir']
        except Exception as e:
            print(f"Failed to load log config: {e}")
    return log_dir

# 日志目录
LOG_DIR = get_log_dir()

# 日志格式
# 参考标准格式: [Time] [Level] [File:Line] Message
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

class ColoredFormatter(logging.Formatter):
    """
    终端彩色日志格式化器
    """
    # ANSI 转义码颜色
    GREY = "\x1b[38;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"
    BLUE = "\x1b[34;20m"

    COLORS = {
        logging.DEBUG: GREY,
        logging.INFO: BLUE,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED
    }

    def format(self, record):
        log_fmt = self.COLORS.get(record.levelno, self.RESET) + LOG_FORMAT + self.RESET
        formatter = logging.Formatter(log_fmt, DATE_FORMAT)
        return formatter.format(record)

class Logger:
    @staticmethod
    def get_logger(name="root"):
        """
        获取配置好的 logger 实例
        """
        logger = logging.getLogger(name)
        
        # 如果已经有 handler 说明配置过了，直接返回
        if logger.handlers:
            return logger
            
        logger.setLevel(logging.DEBUG)

        # 1. Console Handler (输出到控制台)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO) # 控制台默认显示 INFO 及以上
        console_handler.setFormatter(ColoredFormatter()) # 使用彩色格式化器
        logger.addHandler(console_handler)

        # 2. File Handler (输出到文件)
        # 确保目录存在
        if not os.path.exists(LOG_DIR):
            try:
                os.makedirs(LOG_DIR)
            except OSError:
                pass # 可能没有权限或已存在
        
        log_file = os.path.join(LOG_DIR, "system.log")
        try:
            # 轮转日志：每个文件最大 10MB，保留 5 个备份
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG) # 文件记录所有细节
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT)) # 文件使用标准格式
            logger.addHandler(file_handler)
        except Exception as e:
            # 如果文件创建失败，至少保证控制台能用
            console_handler.setLevel(logging.DEBUG)
            logger.warning(f"Failed to create file handler: {e}")

        return logger

# 便捷导出
def get_logger(name):
    return Logger.get_logger(name)
