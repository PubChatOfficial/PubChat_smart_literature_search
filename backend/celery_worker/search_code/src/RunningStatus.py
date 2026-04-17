from enum import Enum

# 1. 定义枚举
class Status(Enum):
    # 'Pending' | 'Running' | 'Success' | 'Failed'
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCESS = "Success"
    FAILED = "Failed"