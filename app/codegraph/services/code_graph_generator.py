import os
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import traceback
from .neo4j_client import Neo4jClient
from app.config.settings import settings
from app.codeast.services.ast_analyzer import FolderAstAnalyzer, FileAstAnalyzer
from app.logger import logger
from app.codegraph.schemes.scheme import QueryResponse, FunctionRequest, ClassRequest

# 导入其他语言的分析器...

class CodeGraphGenerator:
    def __init__(self, repo_id: str, repo_path: str):
        """初始化代码图谱生成器"""
        self.project_id = repo_id
        self.project_dir = repo_path
        self.project_name = os.path.basename(repo_path.rstrip(os.sep))
        
        self.db_client = Neo4jClient(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password
        )

    def __exit__(self, exc_type, exc_val, exc_tb):  
        if self.db_client:
            self.db_client.close()
            self.db_client = None

    async def generate_graph(self, clean_stale: bool = False):
        """生成或更新完整的代码知识图谱"""
        start_time = datetime.now().isoformat()

        # 创建或更新项目节点
        self.db_client.save_project(
            self.project_id,
            self.project_name,
            self.project_dir
        )
        
        # 从项目根目录开始分析
        code_folder_analyzer = FolderAstAnalyzer(self.project_dir, self.project_dir)
        root_folder = await code_folder_analyzer.analyze_folder()
        
        # 保存文件夹结构
        self.db_client.save_folder_node(self.project_id, root_folder)
        
        # 清理过期节点
        if clean_stale:
            self.db_client.delete_stale_nodes(self.project_id, start_time)
        
        return root_folder

    async def update_files(self, file_paths: List[str]):
        """增量更新指定文件
        
        处理流程：
        1. 删除每个文件相关的所有节点（函数、类、方法等）
        2. 重新分析文件生成新的节点
        3. 保存新的节点到图谱
        
        Args:
            file_paths: 需要更新的文件路径列表
        """
        for file_path in file_paths:
            if not os.path.isfile(file_path):
                continue
            
            # 转换为相对路径（与保存时一致）
            rel_path = os.path.relpath(file_path, self.project_dir)
            
            try:
                # 1. 删除文件相关的所有节点
                self.db_client.delete_file_nodes(self.project_id, rel_path)
                
                # 2. 重新分析文件
                file_ast_analyzer = FileAstAnalyzer(self.project_dir, file_path)
                file_node = await file_ast_analyzer.analyze_file()
                
                # 3. 保存新的节点
                if file_node:
                    self.db_client.save_file_node(self.project_id, file_node)
            except Exception as e:
                # 记录错误但继续处理其他文件
                logger.error(f"Error updating file {file_path}: {str(e)}")
                continue

    async def update_folders(self, folder_paths: List[str]):
        """增量更新指定文件夹
        
        处理流程：
        1. 删除每个文件夹相关的所有节点（包括子文件夹、文件、函数、类、方法等）
        2. 重新分析文件夹生成新的节点
        3. 保存新的节点到图谱
        
        Args:
            folder_paths: 需要更新的文件夹路径列表
        """
        for folder_path in folder_paths:
            if not os.path.isdir(folder_path):
                continue
            
            # 转换为相对路径（与保存时一致）
            rel_path = os.path.relpath(folder_path, self.project_dir)
            
            try:
                # 1. 删除文件夹相关的所有节点
                self.db_client.delete_folder_nodes(self.project_id, rel_path)
                
                # 2. 重新分析文件夹
                folder_ast_analyzer = FolderAstAnalyzer(self.project_dir, folder_path)
                folder_node = await folder_ast_analyzer.analyze_folder()
                
                # 3. 保存新的节点
                if folder_node:
                    self.db_client.save_folder_node(self.project_id, folder_node)
            except Exception as e:
                # 记录错误但继续处理其他文件夹
                logger.error(f"Error updating folder {folder_path}: {str(e)}")
                continue

    async def query_project_summary(self) -> QueryResponse:
        """查询项目模块定义和主要功能"""
        try:
            records = self.db_client.query_project_summary(self.project_id)
            
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

    async def query_file_summary(self, file_paths: List[str]) -> QueryResponse:
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
            # 统一file_path路径中分割符，并转换为项目的相对路径
            file_paths = [os.path.relpath(os.path.normpath(path), self.project_dir) for path in file_paths]

            records = self.db_client.query_file_summary(self.project_id, file_paths)
            
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
    
    async def query_functions_code(self, file_functions: List[Dict[str, str]]) -> QueryResponse:
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
            project_id = project_info.generate_project_id()

            # 统一file_path路径中分割符
            file_functions = [
                FunctionRequest(file_path=os.path.relpath(os.path.normpath(file_function.file_path), self.project_dir), function_name=file_function.function_name) 
                for file_function in file_functions]

            records = self.db_client.query_functions_code(project_id, file_functions)
            
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
            project_id = project_info.generate_project_id()

            # 统一file_path路径中分割符
            file_classes = [
                ClassRequest(file_path=os.path.normpath(file_class.file_path), class_name=file_class.class_name) 
                for file_class in file_classes]

            records = self.db_client.query_class_code(project_id, file_classes)
            
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
