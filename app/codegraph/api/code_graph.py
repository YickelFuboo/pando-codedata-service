import os
from fastapi import APIRouter, HTTPException, Body
from app.codegraph.schemes.scheme import (ProjectInfo,
                    GraphGenerateResponse, 
                    PathRequest, 
                    UpdateResponse, 
                    QueryResponse, 
                    FileFunctionRequest, 
                    FileClassRequest,)
from app.codegraph.services.code_graph_generator import CodeGraphGenerator
from app.codegraph.services.code_graph_query import CodeGraphQuery


router = APIRouter()
@router.post("/codegraph/generate",
    summary="生成代码知识图谱",
    description="为指定项目目录生成代码知识图谱",
    response_model=GraphGenerateResponse)
async def generate_graph(request: ProjectInfo = Body(...)):
    """生成代码知识图谱"""
    # 规范化路径
    project_dir = os.path.normpath(request.project_dir)
    
    if not os.path.exists(project_dir):
        raise HTTPException(
            status_code=400,
            detail=f"Project directory not found: {project_dir}"
        )
    
    try:
        generator = CodeGraphGenerator(project_id=request.project_id, project_dir=request.project_dir)
        await generator.generate_graph()
        
        return GraphGenerateResponse(
            status="success",
            message="Code graph generated successfully",
            project_dir=project_dir
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate code graph: {str(e)}"
        )

@router.post("/codegraph/update/files",
    summary="增量更新指定文件",
    description="删除指定文件的图谱数据并重新生成",
    response_model=UpdateResponse)
async def update_files(request: PathRequest):
    """
    增量更新指定文件的代码知识图谱
    
    处理流程：
    1. 删除每个文件相关的所有节点（函数、类、方法等）
    2. 重新分析文件生成新的节点
    3. 保存新的节点到图谱
    """
    # 规范化路径
    project_dir = os.path.normpath(request.project_dir)
    if not os.path.exists(project_dir):
        raise HTTPException(
            status_code=400,
            detail=f"Project directory not found: {project_dir}"
        )
    
    try:
        generator = CodeGraphGenerator(project_id=request.project_id, project_dir=request.project_dir)
        await generator.update_files(request.paths)

        return UpdateResponse(
            status="success",
            message="Files updated successfully",
            updated_paths=request.paths
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update files: {str(e)}"
        )

@router.post("/codegraph/update/folders",
    summary="增量更新指定文件夹",
    description="删除指定文件夹的图谱数据并重新生成",
    response_model=UpdateResponse)
async def update_folders(request: PathRequest):
    """
    增量更新指定文件夹的代码知识图谱
    
    处理流程：
    1. 删除每个文件夹相关的所有节点（包括子文件夹、文件、函数、类、方法等）
    2. 重新分析文件夹生成新的节点
    3. 保存新的节点到图谱
    """
    # 规范化路径
    project_dir = os.path.normpath(request.project_dir)
    if not os.path.exists(project_dir):
        raise HTTPException(
            status_code=400,
            detail=f"Project directory not found: {project_dir}"
        )
    
    try:
        generator = CodeGraphGenerator(project_id=request.project_id, project_dir=request.project_dir)
        await generator.update_folders(request.paths)
        
        return UpdateResponse(
            status="success",
            message="Folders updated successfully",
            updated_paths=request.folder_paths
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update folders: {str(e)}"
        )

@router.post("/codegraph/projects/summary",
    summary="查询项目模块定义和主要功能",
    response_model=QueryResponse)
async def get_project_summary(request: ProjectInfo):
    """获取项目的模块定义和主要功能"""
    with CodeGraphQuery() as query:
        return await query.query_project_summary(project_info = request)

@router.post("/codegraph/files/summary",
    summary="查询文件内容概述",
    response_model=QueryResponse)
async def get_files_summary(request: PathRequest):
    """获取指定文件的内容概述，包含函数和类的清单"""
    with CodeGraphQuery() as query:
        return await query.query_file_summary(project_info = request, file_paths = request.paths)

@router.post("/codegraph/functions/code",
    summary="查询函数实现源码",
    response_model=QueryResponse)
async def get_functions_code(request: FileFunctionRequest):
    """获取指定函数的实现源码
    
    Args:
        request: 包含项目信息和要查询的函数列表
        
    Returns:
        QueryResponse: 包含函数的完整信息，格式为：
            {
                'result': True,
                'content': [
                    {
                        'file_path': 'app/models/user.py',
                        'name': 'create_user',
                        'source_code': '...',
                        'signature': '...',
                        'docstring': '...'
                    }
                ]
            }
    """
    with CodeGraphQuery() as query:
        return await query.query_functions_code(project_info = request, file_functions = request.file_functions)

@router.post("/codegraph/classes/code",
    summary="查询类实现源码",
    response_model=QueryResponse)
async def get_classes_code(request: FileClassRequest):
    """获取指定类的实现源码
    
    Args:
        request: 包含项目信息和要查询的类列表
        
    Returns:
        QueryResponse: 包含类的完整信息，格式为：
            {
                'result': True,
                'content': [
                    {
                        'file_path': 'app/models/user.py',
                        'name': 'UserModel',
                        'source_code': '...',
                        'docstring': '...'
                    }
                ]
            }
    """
    with CodeGraphQuery() as query:
        return await query.query_class_code(project_info = request, file_classes = request.file_classes) 
