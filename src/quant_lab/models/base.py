from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd


class BaseModel(ABC):
    """所有模型预测的基类"""

    def __init__(self,
                 name: str,
                 params: dict[str. Any] | None = None,
                 ) -> None:
        self.name               = name
        self.params             = params
        self.model: Any | None  = None      # 底层真实模型
        self.is_fitted: bool    = False     # 状态标记, 防止还没训练就返回 None



class BaseTrain(ABC):
    """所有模型训练的基类"""