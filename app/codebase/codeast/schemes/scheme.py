from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class AnalyzeFileRequest(BaseModel):
    """文件分析请求"""
    base_path: str = Field(..., description="项目根路径（绝对路径）")
    file_path: str = Field(..., description="要分析的文件路径（绝对路径）")

class AnalyzeFolderRequest(BaseModel):
    """目录分析请求"""
    base_path: str = Field(..., description="项目根路径（绝对路径）")
    folder_path: str = Field(..., description="要分析的目录路径（绝对路径）")

class CallInfoResponse(BaseModel):
    """函数调用信息响应"""
    name: str
    full_name: str
    signature: str

class FunctionInfoResponse(BaseModel):
    """函数信息响应"""
    project_id: Optional[str] = None
    name: str
    full_name: str
    signature: str
    type: str
    source_code: Optional[str] = None
    params: List[str] = []
    param_types: List[str] = []
    returns: List[str] = []
    return_types: List[str] = []
    file_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    summary: Optional[str] = None
    docstring: Optional[str] = None
    class_name: Optional[str] = None
    accessed_attrs: Optional[List[str]] = None
    api_doc: Optional[str] = None
    calls: Optional[List[CallInfoResponse]] = None

class ClassInfoResponse(BaseModel):
    """类信息响应"""
    project_id: Optional[str] = None
    name: str
    full_name: str
    file_path: Optional[str] = None
    node_type: Optional[str] = None
    source_code: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    summary: Optional[str] = None
    methods: Optional[List[FunctionInfoResponse]] = None
    attributes: Optional[List[str]] = None
    base_classes: Optional[List['ClassInfoResponse']] = None
    docstring: Optional[str] = None

ClassInfoResponse.model_rebuild()

class FileInfoResponse(BaseModel):
    """文件信息响应"""
    file_path: str
    language: str
    summary: str
    functions: List[FunctionInfoResponse] = []
    classes: List[ClassInfoResponse] = []
    imports: List[str] = []

class FolderInfoResponse(BaseModel):
    """文件夹信息响应"""
    name: Optional[str] = None
    path: str
    summary: str
    files: List[FileInfoResponse] = []
    subfolders: List['FolderInfoResponse'] = []

FolderInfoResponse.model_rebuild()

class AnalyzeFileResponse(BaseModel):
    """文件分析响应"""
    status: str = Field(default="success", description="状态")
    message: str = Field(default="", description="消息")
    data: Optional[FileInfoResponse] = Field(default=None, description="文件分析结果")

class AnalyzeFolderResponse(BaseModel):
    """目录分析响应"""
    status: str = Field(default="success", description="状态")
    message: str = Field(default="", description="消息")
    data: Optional[FolderInfoResponse] = Field(default=None, description="目录分析结果")

