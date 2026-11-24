"""PySRIM：SRIM 计算的 Python 封装。

此前本模块仅有 ``from .routine import *``，公共 API 依赖 star-import 的副作用，
现已显式导出，保持 ``from srim import SRIM, Target, Layer, Ion`` 可用。
"""

from .core.element import Element
from .core.elementdb import ElementDB
from .core.ion import Ion
from .core.layer import Layer
from .core.material import Material
from .core.target import Target
from .output import Results
from .routine import auto_angle, auto_ions, auto_steps, merge_results, run_calculation
from .srim import SR, SRIM

__all__ = [
    "Element",
    "ElementDB",
    "Ion",
    "Layer",
    "Material",
    "Target",
    "Results",
    "SR",
    "SRIM",
    "auto_angle",
    "auto_ions",
    "auto_steps",
    "merge_results",
    "run_calculation",
]
