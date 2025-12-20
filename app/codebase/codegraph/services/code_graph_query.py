from enum import Enum
from typing import List, Dict, Optional, Any
import os
from .neo4j_client import Neo4jClient
from app.config.settings import settings
from app.codegraph.schemes.scheme import ProjectInfo, QueryResponse, FunctionRequest, ClassRequest


class CodeGraphQuery:
    def __init__(self):
        """初始化查询工具"""
        self.db_client = Neo4jClient(
            settings.get("NEO4J_URI"),
            settings.get("NEO4J_USER"),
            settings.get("NEO4J_PASSWORD")
        )
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):  
        if self.db_client:
            self.db_client.close()
            self.db_client = None
    
    async def query_project_summary(self, project_info: ProjectInfo) -> QueryResponse:
        """查询项目模块定义和主要功能"""
        try:
            records = self.db_client.query_project_summary(project_info.project_id)
            
            # 构建目录树
            folder_map = {}
            root_folders = []
            
            # 1. 先创建所有文件夹节点
            for record in records:
                folder = {
                    'path': record['path'],
                    'name': record['name'],
                    'description': record['description'],
                    'files': record['files']  # 保存当前目录下的文件列表
                }
                folder_map[record['path']] = folder
                
                # 找父文件夹
                parent_path = os.path.dirname(record['path'])
                if parent_path in folder_map:
                    if 'children' not in folder_map[parent_path]:
                        folder_map[parent_path]['children'] = []
                    folder_map[parent_path]['children'].append(folder)
                else:
                    root_folders.append(folder)
            
            # 将列表包装在字典中
            return QueryResponse(
                result=True,
                content=root_folders
            )
        except Exception as e:
            return QueryResponse(
                result=False,
                content={},
                message=f"Failed to query project modules: {str(e)}"
            )

    async def query_file_summary(self, project_info: ProjectInfo, file_paths: List[str]) -> QueryResponse:
        """查询文件内容概述，包含函数和类的清单
        
        Args:
            project_id: 项目ID
            file_paths: 文件路径列表
            
        Returns:
            QueryResponse: 包含每个文件的概述信息，包括：
            - 文件基本信息
            - 类清单（包含方法）
            - 顶层函数清单
        """
        try:
            # 统一file_path路径中分割符
            file_paths = [os.path.normpath(path) for path in file_paths]

            records = self.db_client.query_file_summary(project_info.project_id, file_paths)
            
            files_summary = {}
            for record in records:
                files_summary[record['path']] = {
                    'name': record['name'],
                    'language': record['language'],
                    'summary': record['summary'],
                    'classes': [
                        {
                            'name': cls['name'],
                            'full_name': cls['full_name'],
                            'summary': cls['summary'],
                            'methods': [
                                m for m in cls['methods']
                                if m['name'] is not None  # 过滤无效方法
                            ]
                        }
                        for cls in record['classes']
                        if cls['name'] is not None  # 过滤无效类
                    ],
                    'functions': [
                        func for func in record['functions']
                        if func['name'] is not None  # 过滤无效函数
                    ]
                }
            
            return QueryResponse(
                result=True,
                content={
                    'files': files_summary
                }
            )
        except Exception as e:
            return QueryResponse(
                result=False,
                content={},
                message=f"Failed to query file summary: {str(e)}"
            )
    
    async def query_functions_code(self, project_info: ProjectInfo, file_functions: List[Dict[str, str]]) -> QueryResponse:
        """查询指定函数的实现源码
        
        Args:
            project_id: 项目ID
            file_functions: 文件和函数的对应关系列表，格式为：
                [
                    {
                        "file_path": "app/models/user.py",     # 文件相对路径
                        "function_name": "create_user"         # 函数名称
                    }
                ]
        
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
        try:
            # 统一file_path路径中分割符
            file_functions = [
                FunctionRequest(file_path=os.path.normpath(file_function.file_path), function_name=file_function.function_name) 
                for file_function in file_functions]

            records = self.db_client.query_functions_code(project_info.project_id, file_functions)
            
            # 转换为列表格式，更适合前端处理
            functions_list = []
            for record in records:
                functions_list.append({
                    'file_path': record['file_path'],
                    'name': record['name'],
                    'source_code': record['details']['source_code'],
                    'signature': record['details']['signature'],
                    'docstring': record['details']['docstring']
                })
            
            return QueryResponse(
                result=True,
                content=functions_list
            )
        except Exception as e:
            return QueryResponse(
                result=False,
                content=[],
                message=f"Failed to query functions code: {str(e)}"
            )

    async def query_class_code(self, project_info: ProjectInfo, file_classes: List[Dict[str, str]]) -> QueryResponse:
        """查询指定类的实现源码
        
        Args:
            project_id: 项目ID
            file_classes: 文件和类的对应关系列表，格式为：
                [
                    {
                        "file_path": "/app/models/user.py",
                        "class_name": "UserModel"
                    }
                ]
        
        Returns:
            QueryResponse: 包含类的完整信息
        """
        try:
            # 统一file_path路径中分割符
            file_classes = [
                ClassRequest(file_path=os.path.normpath(file_class.file_path), class_name=file_class.class_name) 
                for file_class in file_classes]

            records = self.db_client.query_class_code(project_info.project_id, file_classes)
            
            classes = {}
            for record in records:
                file_path = record['file_path']
                if file_path not in classes:
                    classes[file_path] = {}
                classes[file_path][record['name']] = record['details']
            
            return QueryResponse(
                result=True,
                content={
                    'classes': classes
                }
            )
        except Exception as e:
            return QueryResponse(
                result=False,
                content={},
                message=f"Failed to query class code: {str(e)}"
            )