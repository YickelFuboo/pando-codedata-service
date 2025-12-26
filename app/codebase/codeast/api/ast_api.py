import os
import logging
from fastapi import APIRouter, HTTPException, status, Body
from typing import Optional
from app.codebase.codeast.services.ast_analyzer import FileAstAnalyzer, FolderAstAnalyzer
from app.codebase.codeast.schemes.scheme import (
    AnalyzeFileRequest,
    AnalyzeFolderRequest,
    AnalyzeFileResponse,
    AnalyzeFolderResponse,
    FileInfoResponse,
    FolderInfoResponse,
    FunctionInfoResponse,
    ClassInfoResponse,
    CallInfoResponse
)
from app.codebase.codeast.models.model import (
    FileInfo,
    FolderInfo,
    FunctionInfo,
    ClassInfo,
    CallInfo
)

router = APIRouter(prefix="/codeast", tags=["代码AST分析"])

def _convert_call_info(call_info: CallInfo) -> CallInfoResponse:
    """转换CallInfo为响应模型"""
    return CallInfoResponse(
        name=call_info.name,
        full_name=call_info.full_name,
        signature=call_info.signature
    )

def _convert_function_info(func_info: FunctionInfo) -> FunctionInfoResponse:
    """转换FunctionInfo为响应模型"""
    return FunctionInfoResponse(
        project_id=func_info.project_id,
        name=func_info.name,
        full_name=func_info.full_name,
        signature=func_info.signature,
        type=func_info.type,
        source_code=func_info.source_code,
        params=func_info.params or [],
        param_types=func_info.param_types or [],
        returns=func_info.returns or [],
        return_types=func_info.return_types or [],
        file_path=func_info.file_path,
        start_line=func_info.start_line,
        end_line=func_info.end_line,
        summary=func_info.summary,
        docstring=func_info.docstring,
        class_name=func_info.class_name,
        accessed_attrs=func_info.accessed_attrs,
        api_doc=func_info.api_doc,
        calls=[_convert_call_info(call) for call in func_info.calls] if func_info.calls else None
    )

def _convert_class_info(class_info: ClassInfo) -> ClassInfoResponse:
    """转换ClassInfo为响应模型"""
    return ClassInfoResponse(
        project_id=class_info.project_id,
        name=class_info.name,
        full_name=class_info.full_name,
        file_path=class_info.file_path,
        node_type=class_info.node_type,
        source_code=class_info.source_code,
        start_line=class_info.start_line,
        end_line=class_info.end_line,
        summary=class_info.summary,
        methods=[_convert_function_info(method) for method in class_info.methods] if class_info.methods else None,
        attributes=class_info.attributes,
        base_classes=[_convert_class_info(base) for base in class_info.base_classes] if class_info.base_classes else None,
        docstring=class_info.docstring
    )

def _convert_file_info(file_info: FileInfo) -> FileInfoResponse:
    """转换FileInfo为响应模型"""
    return FileInfoResponse(
        file_path=file_info.file_path,
        language=file_info.language,
        summary=file_info.summary or "",
        functions=[_convert_function_info(func) for func in file_info.functions] if file_info.functions else [],
        classes=[_convert_class_info(cls) for cls in file_info.classes] if file_info.classes else [],
        imports=file_info.imports or []
    )

def _convert_folder_info(folder_info: FolderInfo) -> FolderInfoResponse:
    """转换FolderInfo为响应模型"""
    folder_name = getattr(folder_info, 'name', None)
    if not folder_name and folder_info.path:
        folder_name = os.path.basename(folder_info.path.rstrip(os.sep))
    
    return FolderInfoResponse(
        name=folder_name,
        path=folder_info.path,
        summary=folder_info.summary or "",
        files=[_convert_file_info(file) for file in folder_info.files] if folder_info.files else [],
        subfolders=[_convert_folder_info(subfolder) for subfolder in folder_info.subfolders] if folder_info.subfolders else []
    )

@router.post("/analyze/file", response_model=AnalyzeFileResponse, status_code=status.HTTP_200_OK)
async def analyze_file(request: AnalyzeFileRequest = Body(...)):
    """
    分析指定文件的AST结构
    
    - **base_path**: 项目根路径（绝对路径）
    - **file_path**: 要分析的文件路径（绝对路径）
    
    返回文件的函数、类、导入等信息
    """
    try:
        base_path = os.path.normpath(request.base_path)
        file_path = os.path.normpath(request.file_path)
        
        if not os.path.exists(base_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"项目根路径不存在: {base_path}"
            )
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件路径不存在: {file_path}"
            )
        
        if not os.path.isfile(file_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"指定路径不是文件: {file_path}"
            )
        
        if not file_path.startswith(base_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件路径不在项目根路径下: {file_path}"
            )
        
        analyzer = FileAstAnalyzer(base_path, file_path)
        file_info = await analyzer.analyze_file()
        
        if file_info is None:
            return AnalyzeFileResponse(
                status="warning",
                message="文件分析失败或文件类型不支持",
                data=None
            )
        
        response_data = _convert_file_info(file_info)
        
        return AnalyzeFileResponse(
            status="success",
            message="文件分析成功",
            data=response_data
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"分析文件时发生错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分析文件失败: {str(e)}"
        )

@router.post("/analyze/folder", response_model=AnalyzeFolderResponse, status_code=status.HTTP_200_OK)
async def analyze_folder(request: AnalyzeFolderRequest = Body(...)):
    """
    分析指定目录的AST结构
    
    - **base_path**: 项目根路径（绝对路径）
    - **folder_path**: 要分析的目录路径（绝对路径）
    
    返回目录下所有文件的分析结果，包括子目录
    """
    try:
        base_path = os.path.normpath(request.base_path)
        folder_path = os.path.normpath(request.folder_path)
        
        if not os.path.exists(base_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"项目根路径不存在: {base_path}"
            )
        
        if not os.path.exists(folder_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"目录路径不存在: {folder_path}"
            )
        
        if not os.path.isdir(folder_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"指定路径不是目录: {folder_path}"
            )
        
        if not folder_path.startswith(base_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"目录路径不在项目根路径下: {folder_path}"
            )
        
        analyzer = FolderAstAnalyzer(base_path, folder_path)
        folder_info = await analyzer.analyze_folder()
        
        if folder_info is None:
            return AnalyzeFolderResponse(
                status="warning",
                message="目录分析失败",
                data=None
            )
        
        response_data = _convert_folder_info(folder_info)
        
        return AnalyzeFolderResponse(
            status="success",
            message="目录分析成功",
            data=response_data
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"分析目录时发生错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分析目录失败: {str(e)}"
        )

