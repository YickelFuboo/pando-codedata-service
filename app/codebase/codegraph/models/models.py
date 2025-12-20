from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class RelationType:
    # 结构关系
    CONTAINS = "CONTAINS"       # 表示所有包含关系：
                               # - Project包含Folder/File
                               # - Folder包含Folder/File
                               # - File包含Class/Function
                               # - Class包含Method
    
    # 依赖关系
    DEPENDS_ON = "DEPENDS_ON"   # 类之间的依赖关系（通过方法调用产生）
    IMPORTS = "IMPORTS"         # 文件间的导入依赖
    
    # 调用关系
    CALLS = "CALLS"            # 函数调用关系（包括普通函数、类方法和API调用）
    
    # 继承关系
    INHERITS = "INHERITS"      # 类继承
    IMPLEMENTS = "IMPLEMENTS"   # 接口实现
    OVERRIDES = "OVERRIDES"    # 方法重写父类方法