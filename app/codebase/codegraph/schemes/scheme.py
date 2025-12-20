from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any    
import os
import hashlib
from dataclasses import dataclass

class ProjectInfo(BaseModel):
    """项目信息"""
    project_id: str = Field(..., description="项目ID")
    project_dir: str = Field(..., description="项目根路径")

class GraphGenerateResponse(BaseModel):
    """图谱生成响应"""
    status: str
    message: str
    project_dir: str

class PathRequest(ProjectInfo):
    """文件夹/文件更新请求"""
    paths: List[str] = Field(..., description="需要更新的文件夹/文件路径列表")

class UpdateResponse(BaseModel):
    """更新响应"""
    status: str
    message: str
    updated_paths: List[str]

# 修改这里：让 QueryResponse 继承 BaseModel
@dataclass
class QueryResponse():
    """统一的查询响应格式"""
    result: bool
    content: Dict[str, Any]
    message: str = ""

class FunctionRequest(BaseModel):
    """函数请求信息"""
    file_path: str = Field(..., description="文件相对路径，例如: 'app/models/user.py'")
    function_name: str = Field(..., description="函数名称，例如: 'create_user'")

class FileFunctionRequest(ProjectInfo):
    """函数代码查询请求"""
    file_functions: List[FunctionRequest] = Field(
        ..., 
        description="要查询的文件和函数列表",
        example=[
            {
                "file_path": "app/models/user.py",
                "function_name": "create_user"
            },
            {
                "file_path": "app/services/auth.py",
                "function_name": "verify_token"
            }
        ]
    )

class ClassRequest(BaseModel):
    """类请求信息"""
    file_path: str = Field(..., description="文件相对路径，例如: 'app/models/user.py'")
    class_name: str = Field(..., description="类名称，例如: 'UserModel'")

class FileClassRequest(ProjectInfo):
    """类代码查询请求"""
    file_classes: List[ClassRequest] = Field(
        ..., 
        description="要查询的文件和类列表",
        example=[
            {
                "file_path": "app/models/user.py",
                "class_name": "UserModel"
            },
            {
                "file_path": "app/services/auth.py",
                "class_name": "AuthService"
            }
        ]
    )