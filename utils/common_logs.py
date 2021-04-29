# Logging
import logging
import logging.handlers
import os

_logger = logging.getLogger(__name__)

_formater = logging.Formatter("[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)s] %(message)s")

_streamHandler = logging.StreamHandler()
#_fileHandler = logging.FileHandler("./logs/log.log")
_fileMaxBytes = 1024 * 1024 * 100 # 100mb

current_dir_path = os.path.dirname(os.path.abspath(__file__))
log_dir = current_dir_path + '/../logs'

_fileHandler = logging.handlers.RotatingFileHandler(log_dir+'/log.log', maxBytes=_fileMaxBytes, backupCount=0)

_streamHandler.setFormatter(_formater)
_fileHandler.setFormatter(_formater)

_logger.addHandler(_streamHandler)
_logger.addHandler(_fileHandler)

_logger.setLevel(level=logging.DEBUG)
