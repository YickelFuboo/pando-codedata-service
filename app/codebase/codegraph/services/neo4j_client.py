import os
from neo4j import GraphDatabase
from typing import Dict, List, Union, Optional
from dataclasses import asdict
import logging
from app.codeast.models.model import FileInfo, FunctionInfo, ClassInfo, FolderInfo, CallInfo
from app.codegraph.schemes.scheme import FunctionRequest, ClassRequest


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def close(self):
        self.driver.close()
        
    def save_project(self, project_id: str, name: str, root_path: str):
        """创建或更新项目
        
        Args:
            project_id: 项目全局唯一标识符
            name: 项目名称
            root_path: 项目根路径
        """
        with self.driver.session() as session:
            try:
                # 1. 创建或更新项目节点
                session.run("""
                    MERGE (p:Project {project_id: $project_id})
                    SET p.name = $name,
                    p.root_path = $root_path,
                    p.updated_at = datetime()
                    WITH p
                    WHERE p.created_at IS NULL
                    SET p.created_at = datetime()
                    RETURN p
                """, {
                    'project_id': project_id,
                    'name': name,
                    'root_path': root_path
                })
            
            except Exception as e:
                logging.error(f"Error in save_project: {str(e)}, project_id: {project_id}, name: {name}")
                logging.error(f"Error type: {type(e)}")
                raise
    def save_folder_node(self, project_id: str, folder_node: FolderInfo, parent_folder_node: FolderInfo = None):
        """保存完整的文件夹结构
        1. 文件夹节点
        2. 根文件夹，Project=>(CONTAINS)=>文件夹节点
        3. 子文件夹节点
        4. 子文件夹：文件夹=>(CONTAINS)=>子文件夹、子文件
        5. 文件节点每分析一个就会保存一个，避免积累，这里仅更新文件节点与文件夹的关系"""
        with self.driver.session() as session:
            try:
                # 1. 保存文件夹节点
                session.run("""
                    MERGE (folder:Folder {
                        project_id: $project_id,
                        name: $name,
                        path: $path
                    })
                    SET folder.summary = $summary,                    
                        folder.display_name = $name,
                        folder.updated_at = datetime()
                    WITH folder
                    WHERE folder.created_at IS NULL
                    SET folder.created_at = datetime()
                """, {
                    'project_id': project_id,
                    'name': folder_node.name,
                    'path': folder_node.path,
                    'summary': folder_node.summary
                })

                # 如果存在父文件夹节点，则创建parent_folder_node与folder_node的关系
                # 否则，创建folder_node与Project的关系
                if parent_folder_node and parent_folder_node.name != "":
                    session.run("""
                        MATCH (parent:Folder {
                            project_id: $project_id,
                            name: $parent_name,
                            path: $parent_path
                        }) 
                        MATCH (child:Folder {
                            project_id: $project_id,
                            name: $child_name,
                            path: $child_path
                        })
                        MERGE (parent)-[:CONTAINS]->(child)
                    """, {
                        'project_id': project_id, 
                        'parent_name': parent_folder_node.name,
                        'parent_path': parent_folder_node.path,
                        'child_name': folder_node.name,
                        'child_path': folder_node.path
                    })  
                else:
                    session.run("""
                        MATCH (p:Project {project_id: $project_id})
                        MATCH (folder:Folder {
                            project_id: $project_id,
                            name: $name,
                            path: $path
                        })
                        MERGE (p)-[:CONTAINS]->(folder)
                    """, {
                        'project_id': project_id,
                        'name': folder_node.name,
                        'path': folder_node.path
                    })

                # 2. 递归处理子文件夹
                for subfolder in folder_node.subfolders:
                    # 先保存子文件夹
                    self.save_folder_node(project_id, subfolder, folder_node)
            
                # 3. 保存文件节点及其内容
                for file in folder_node.files:
                    # 文件每次分析完毕后先保存，这里补充重复保存
                    #self.save_file_node(project_id, file)
                    self._update_folder_contains_file(project_id, folder_node, file)
                
            except Exception as e:
                logging.error(f"Error in save_folder_node: {str(e)}, folder_node: {folder_node}")
                logging.error(f"Error type: {type(e)}")
                raise
    
    # 更新FolderNode与FileNode的关系
    def _update_folder_contains_file(self, project_id: str, folder_node: FolderInfo, file_node: FileInfo):
        """更新FolderNode与FileNode的关系"""
        with self.driver.session() as session:
            try:
                # 创建文件夹与文件的关系
                session.run("""
                    MATCH (folder:Folder {
                        project_id: $project_id,
                        name: $folder_name,
                        path: $folder_path
                    })
                    MATCH (file:File {
                        project_id: $project_id,
                        name: $name,
                        file_path: $file_path
                    })
                    MERGE (folder)-[:CONTAINS]->(file)
                """, {
                    'project_id': project_id,
                    'folder_name': folder_node.name,
                    'folder_path': folder_node.path,
                    'name': file_node.name,
                    'file_path': file_node.file_path
                })
            except Exception as e:
                logging.error(f"Error in update_folder_contains_file: {str(e)}, folder_node: {folder_node}, file_node: {file_node}")
                logging.error(f"Error type: {type(e)}")
                raise

    def save_file_node(self, project_id: str, file_node: FileInfo):
        """保存文件节点及其包含的函数和类"""
        with self.driver.session() as session:
            try:
                # 1. 创建 File 节点
                session.run("""
                    MERGE (f:File {
                        project_id: $project_id,
                        name: $name,
                        file_path: $file_path
                    })
                    SET f.language = $language,
                        f.summary = $summary,
                        f.imports = $imports,
                        f.display_name = $name,
                        f.updated_at = datetime()
                    WITH f
                    WHERE f.created_at IS NULL
                    SET f.created_at = datetime()
                    RETURN f
                """, {
                    'project_id': project_id,
                    'name': file_node.name,
                    'file_path': file_node.file_path,
                    'language': file_node.language,
                    'summary': file_node.summary,
                    'imports': file_node.imports
                })

                # 2. 保存文件中的类和函数节点            
                if file_node.classes:
                    for class_node in file_node.classes:
                        if isinstance(class_node, ClassInfo):
                            self.save_class_node(project_id, file_node, class_node)
                        else:
                            logging.warning(f"Invalid class node type: {type(class_node)}")
                        
                if file_node.functions:
                    for func_node in file_node.functions:
                        if isinstance(func_node, FunctionInfo):
                            self.save_function_node(project_id, file_node, func_node)
                        else:
                            logging.warning(f"Invalid function node type: {type(func_node)}")

            except Exception as e:
                logging.error(f"Error in save_file_node: {str(e)}")
                logging.error(f"Error type: {type(e)}")
                logging.error(f"File node: {file_node}")
                raise
    
    def save_class_node(self, project_id: str, file_node: FileInfo, class_node: ClassInfo):
        """保存类节点及其方法"""
        with self.driver.session() as session:
            try:                
                # 1. 创建 Class 节点                
                class_data = asdict(class_node)
                session.run("""
                    MERGE (c:Class {
                        project_id: $project_id,
                        name: $name,
                        full_name: $full_name
                    })
                    SET c.file_path = $file_path,
                        c.node_type = $node_type,
                        c.docstring = $docstring,
                        c.source_code = $source_code,
                        c.summary = $summary,
                        c.attributes = $attributes,
                        c.display_name = $name,
                        c.updated_at = datetime()
                    WITH c
                    WHERE c.created_at IS NULL
                    SET c.created_at = datetime()
                    RETURN c
                """, {
                    'project_id': project_id,
                    'file_path': file_node.file_path,
                    **class_data
                })
                
                # 2. 建立与文件的关系
                session.run("""
                    MATCH (f:File {project_id: $project_id, name: $file_name, file_path: $file_path})
                    MATCH (c:Class {project_id: $project_id, name: $class_name, full_name: $class_full_name})
                    MERGE (f)-[:CONTAINS]->(c)
                """, {
                    'project_id': project_id,
                    'file_name': file_node.name,
                    'file_path': file_node.file_path,
                    'class_name': class_node.name,
                    'class_full_name': class_node.full_name
                })

                # 3. 处理继承关系（如果有）
                if class_node.base_classes:
                    self._save_class_inheritance(project_id, class_node)
                
                # 4. 处理类方法
                if class_node.methods:
                    for method_node in class_node.methods:
                        if isinstance(method_node, FunctionInfo):
                            self.save_method_node(project_id, class_node, method_node)
                        else:
                            logging.warning(f"Invalid method node type: {type(method_node)}")    
                
            except Exception as e:
                logging.error(f"Error in save_class_node: {str(e)}")
                logging.error(f"Error type: {type(e)}")
                logging.error(f"File path: {file_node.file_path}")
                logging.error(f"Class node: {class_node}")
                raise

    def _save_class_inheritance(self, project_id: str, class_node: ClassInfo):
        """处理类的继承关系
        
        Args:
            project_id: 项目ID
            class_node: 类节点
        """
        with self.driver.session() as session:
            try:
                session.run("""
                    MATCH (c:Class {project_id: $project_id, name: $name, full_name: $full_name})
                    UNWIND $base_classes as base
                    // 使用 MERGE 而不是 MATCH 来确保父类存在
                    MERGE (base_class:Class {
                        project_id: $project_id,
                        name: base.name,
                        full_name: base.full_name
                    })
                    // 设置父类的基本属性
                    ON CREATE SET 
                        base_class.node_type = base.node_type,
                        base_class.display_name = base.name,
                        base_class.created_at = datetime()
                    SET base_class.updated_at = datetime()
                    
                    WITH c, base_class, base_class.node_type = 'interface' as is_interface
                    FOREACH (x IN CASE WHEN is_interface THEN [1] ELSE [] END |
                        MERGE (c)-[:IMPLEMENTS]->(base_class)
                    )
                    FOREACH (x IN CASE WHEN NOT is_interface THEN [1] ELSE [] END |
                        MERGE (c)-[:INHERITS]->(base_class)
                    )
                """, {
                    'project_id': project_id,
                    'name': class_node.name,
                    'full_name': class_node.full_name,
                    'base_classes': asdict(class_node)['base_classes']
                })
                
            except Exception as e:
                logging.error(f"Error in _save_class_inheritance: {str(e)}")
                logging.error(f"Error type: {type(e)}")
                logging.error(f"Class node: {class_node}")
                raise
    
    def save_function_node(self, project_id: str, file_node: FileInfo, function_node: FunctionInfo):
        """保存函数节点（包括普通函数和类方法）
        
        Args:
            project_id: 项目ID
            file_node: 父节点（文件）
            function_node: 函数节点
            
        处理以下关系：
        1. File -(CONTAINS)-> Function (如果父节点是文件)
        2. Function -(CALLS)-> Function/Method/API (函数调用关系)
        """

        with self.driver.session() as session:
            try:
                # 1. 创建 Function 节点
                function_data = asdict(function_node)
                session.run("""
                    MERGE (f:Function {
                        project_id: $project_id,
                        name: $name,
                        full_name: $full_name,
                        signature: $signature
                    })
                    SET f.file_path = $file_path,
                        f.source_code = $source_code,
                        f.summary = $summary,
                        f.docstring = $docstring,
                        f.params = $params,
                        f.param_types = $param_types,
                        f.returns = $returns,
                        f.return_types = $return_types,
                        f.class_name = $class_name,
                        f.display_name = $name,
                        f.updated_at = datetime()
                    WITH f
                    WHERE f.created_at IS NULL
                    SET f.created_at = datetime()
                """, {
                    'project_id': project_id,
                    'file_path': file_node.file_path,
                    'class_name': '',
                    'parent_type': 'File',
                    **function_data
                })
                    
                # 2. 建立与父节点的关系
                session.run("""
                    MATCH (file:File {project_id: $project_id, name: $file_name, file_path: $file_path})
                    MATCH (f:Function {
                        project_id: $project_id,
                        name: $name,
                        full_name: $full_name,
                        signature: $signature
                    }) 
                    MERGE (file)-[:CONTAINS]->(f)
                """, {
                    'project_id': project_id,
                    'file_name': file_node.name,
                    'file_path': file_node.file_path,
                    'name': function_node.name,
                    'full_name': function_node.full_name,
                    'signature': function_node.signature
                })
                
                # 3. 处理函数调用关系
                if function_node.calls:
                    for call_info in function_node.calls:
                        self._save_function_calls(project_id, function_node, call_info)
                        
            except Exception as e:
                logging.error(f"Error in save_function_node: {str(e)}, function_node: {function_node}")
                logging.error(f"Error type: {type(e)}")
                raise
                              
    def save_method_node(self, project_id: str, class_node: ClassInfo, function_node: FunctionInfo):
        """保存函数节点（包括普通函数和类方法）
        
        Args:
            project_id: 项目ID
            class_node: 父节点（类）
            function_node: 函数节点
            
        处理以下关系：
        1. File -(CONTAINS)-> Function (如果父节点是文件)
        2. Class -(CALLS)-> Method (函数调用关系)
        """

        with self.driver.session() as session:
            try:
                # 1. 创建 Function 节点
                function_data = asdict(function_node)
                session.run("""
                    MERGE (f:Function {
                        project_id: $project_id,
                        name: $name,
                        full_name: $full_name,
                        signature: $signature
                    })
                    SET f.file_path = $file_path,
                        f.source_code = $source_code,
                        f.summary = $summary,
                        f.docstring = $docstring,
                        f.params = $params,
                        f.param_types = $param_types,
                        f.returns = $returns,
                        f.return_types = $return_types,
                        f.class_name = $class_name,
                        f.display_name = $name,
                        f.updated_at = datetime()
                    WITH f
                    WHERE f.created_at IS NULL
                    SET f.created_at = datetime()
                """, {
                    'project_id': project_id,
                    'file_path': class_node.file_path,
                    'class_name': class_node.name, 
                    'parent_type': 'Class',
                    **function_data
                })
                    
                # 2. 建立与父节点的关系
                session.run("""
                    MATCH (c:Class {project_id: $project_id, name: $class_name, full_name: $class_full_name})
                    MATCH (f:Function {
                        project_id: $project_id,
                        name: $name,
                        full_name: $full_name,
                        signature: $signature
                    }) 
                    MERGE (c)-[:CONTAINS]->(f)
                """, {
                    'project_id': project_id,
                    'class_name': class_node.name,
                    'class_full_name': class_node.full_name,
                    'name': function_node.name,
                    'full_name': function_node.full_name,
                    'signature': function_node.signature
                })
                
                # 3. 处理函数调用关系
                if function_node.calls:
                    for call_info in function_node.calls:
                        self._save_function_calls(project_id, function_node, call_info)
                        
            except Exception as e:
                logging.error(f"Error in save_method_node: {str(e)}, function_node: {function_node}")
                logging.error(f"Error type: {type(e)}")
                raise
    
    def _save_function_calls(self, project_id: str, function_node: FunctionInfo, call_info: CallInfo):
        """保存函数的调用关系"""
        with self.driver.session() as session:
            try:
                session.run("""
                    // 找到调用方函数
                    MATCH (caller:Function {
                        project_id: $project_id,
                        name: $caller_name,
                        full_name: $caller_full_name,
                        signature: $caller_signature
                    })
                    
                    // 找到被调用方（可能是函数、方法或API），找不到先按照API方式创建
                    MERGE (callee:Function {
                        project_id: $project_id,
                        name: $callee_name,
                        full_name: $callee_full_name,
                        signature: $callee_signature
                    })
                    ON CREATE SET
                        callee.node_type = 'api',
                        callee.created_at = datetime()
                    SET callee.updated_at = datetime()
                    
                    
                    // 创建调用关系
                    WITH caller, callee
                    MERGE (caller)-[r:CALLS]->(callee)
                """, {
                    'project_id': project_id,
                    'caller_name': function_node.name,
                    'caller_full_name': function_node.full_name,
                    'caller_signature': function_node.signature,
                    'callee_name': call_info.name,
                    'callee_full_name': call_info.full_name,
                    'callee_signature': call_info.signature
                })

            except Exception as e:
                logging.error(f"Error in _save_function_calls: {str(e)}, function_node: {function_node}, call_info: {call_info}")
                logging.error(f"Error type: {type(e)}")
                raise
    
    def delete_stale_nodes(self, project_id: str, before_timestamp: str):
        """删除过期节点（未在最近更新中出现的节点）
        
        删除所有属于指定项目且在指定时间之前未更新的节点及其关系
        """
        with self.driver.session() as session:
            try:
                session.run("""
                    MATCH (n)
                    WHERE n.project_id = $project_id 
                    AND n.updated_at < datetime($before_timestamp)
                    AND NOT n:Project  // 不删除项目节点
                    DETACH DELETE n
                """, {
                    'project_id': project_id,
                    'before_timestamp': before_timestamp
                }) 
            
            except Exception as e:
                logging.error(f"Error in delete_stale_nodes: {str(e)}, project_id: {project_id}, before_timestamp: {before_timestamp}")
                logging.error(f"Error type: {type(e)}")
                raise

    def delete_file_nodes(self, project_id: str, file_path: str):
        """删除文件及其相关节点（函数、类等）
        
        用于文件更新或删除场景。
        DETACH DELETE 会自动处理：
        1. 文件中的节点（函数、类等）
        2. 其他文件对该文件的依赖关系
        3. 其他函数对该文件中函数的调用关系
        4. 其他类对该文件中类的继承关系
        5. 文件节点本身
        """
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                try:
                    tx.run("""
                        MATCH (f:File {
                            project_id: $project_id,
                            file_path: $file_path
                        })-[:CONTAINS]->(n)
                        DETACH DELETE n
                        
                        WITH f
                        DETACH DELETE f
                    """, {
                        'project_id': project_id,
                        'file_path': file_path
                    })
                    tx.commit()
                except Exception as e:
                    tx.rollback()
                    logging.error(f"Error in delete_file_nodes: {str(e)}, project_id: {project_id}, file_path: {file_path}")
                    logging.error(f"Error type: {type(e)}")
                    raise e

    def delete_folder_nodes(self, project_id: str, folder_path: str):
        """删除文件夹及其所有子节点
        
        用于文件夹删除场景。会删除：
        1. 所有子文件夹（通过STARTS WITH匹配）
        2. 所有文件
        3. 文件中的所有函数（包括类方法）和类
        4. 相关的所有关系
        """
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                try:
                    tx.run("""
                        // 1. 匹配目标文件夹及其所有子文件夹
                        MATCH (folder:Folder {project_id: $project_id})
                        WHERE folder.path STARTS WITH $folder_path
                        
                        // 2. 匹配这些文件夹中的所有文件
                        OPTIONAL MATCH (folder)-[:CONTAINS]->(file:File)
                        
                        // 3. 匹配文件中的所有函数和类
                        OPTIONAL MATCH (file)-[:CONTAINS]->(node)
                        WHERE node:Function OR node:Class
                        
                        // 4. 删除所有相关节点（DETACH会删除所有关系）
                        WITH DISTINCT folder, file, node
                        DETACH DELETE node, file, folder
                    """, {
                        'project_id': project_id,
                        'folder_path': folder_path
                    })
                    tx.commit()
                except Exception as e:
                    tx.rollback()
                    logging.error(f"Error in delete_folder_nodes: {str(e)}, project_id: {project_id}, folder_path: {folder_path}")
                    logging.error(f"Error type: {type(e)}")
                    raise e
    
    def query_project_summary(self, project_id: str) -> List[Dict]:
        """查询项目模块定义和主要功能
        
        Returns:
            List[Dict]: 返回所有目录及其直接包含的文件列表，格式为：
            [
                {
                    'path': 'app/models',  # 文件夹路径
                    'name': 'models',      # 文件夹名称
                    'description': '数据模型模块',  # 文件夹描述
                    'files': [             # 当前文件夹下的文件列表
                        {
                            'path': 'app/models/user.py',
                            'name': 'user.py',
                            'description': '用户模型定义'
                        }
                    ]
                }
            ]
        """
        with self.driver.session() as session:
            result = session.run("""
                // 1. 匹配项目下的所有文件夹
                MATCH (folder:Folder)
                WHERE folder.project_id = $project_id
                
                // 2. 获取文件夹直接包含的文件
                OPTIONAL MATCH (folder)-[:CONTAINS]->(file:File)
                
                // 3. 聚合文件夹的直接文件
                WITH folder,
                    collect({
                        path: file.file_path,
                        name: file.name,
                        description: file.summary
                    }) as files
                
                // 4. 返回结果
                RETURN {
                    path: folder.path,
                    name: folder.name,
                    description: folder.summary,
                    files: [f IN files WHERE f.name IS NOT NULL]
                } as result
                ORDER BY folder.path
            """, {'project_id': project_id})
            
            return [record['result'] for record in result]

    def query_file_summary(self, project_id: str, file_paths: List[str]) -> Dict:
        """查询文件内容概述"""
        with self.driver.session() as session:
            result = session.run("""
                // 1. 匹配文件节点
                MATCH (file:File)
                WHERE file.file_path IN $file_paths
                AND file.project_id = $project_id
                
                // 2. 查找文件中的类及其方法
                OPTIONAL MATCH (file)-[:CONTAINS]->(class:Class)
                OPTIONAL MATCH (class)-[:CONTAINS]->(method:Function)
                WITH file, class,
                     collect({
                         name: method.name,
                         signature: method.signature,
                         summary: method.summary,
                         type: method.type
                     }) as methods
                
                // 3. 收集类信息
                WITH file,
                     collect({
                         name: class.name,
                         full_name: class.full_name,
                         summary: class.summary,
                         methods: methods
                     }) as classes
                
                // 4. 查找顶层函数（不属于任何类）
                OPTIONAL MATCH (file)-[:CONTAINS]->(func:Function)
                WHERE NOT EXISTS {
                    MATCH (c:Class)-[:CONTAINS]->(func)
                }
                
                // 5. 返回完整信息
                RETURN file.file_path as path,
                       file.name as name,
                       file.language as language,
                       file.summary as summary,
                       classes,
                       collect({
                           name: func.name,
                           signature: func.signature,
                           summary: func.summary,
                           type: func.type
                       }) as functions
                ORDER BY file.file_path
            """, {
                'project_id': project_id,
                'file_paths': file_paths
            })
            
            return list(result)

    def query_functions_code(self, project_id: str, file_functions: List[FunctionRequest]) -> Dict:
        """查询函数实现源码"""
        with self.driver.session() as session:
            result = session.run("""
                // 1. 匹配文件节点和函数节点
                MATCH (file:File)-[:CONTAINS]->(func:Function)
                WHERE file.project_id = $project_id
                AND {
                    file_path: file.file_path,
                    function_name: func.name
                } IN $file_functions
                
                // 2. 返回函数信息
                RETURN {
                    file_path: file.file_path,
                    name: func.name,
                    details: {
                        source_code: func.source_code,
                        signature: func.signature,
                        docstring: func.docstring
                    }
                } as result
                ORDER BY file.file_path, func.name
            """, {
                'project_id': project_id,
                'file_functions': [
                    {
                        'file_path': os.path.normpath(item.file_path),  # 直接访问 Pydantic 模型属性
                        'function_name': item.function_name  
                    }
                    for item in file_functions
                ]
            })
            
            records = list(result)
            return [record['result'] for record in records]

    def query_class_code(self, project_id: str, file_classes: List[ClassRequest]) -> Dict:
        """查询类实现源码"""
        with self.driver.session() as session:
            result = session.run("""
                // 1. 匹配文件节点和类节点
                MATCH (file:File)-[:CONTAINS]->(class:Class)
                WHERE file.project_id = $project_id
                AND {
                    file_path: file.file_path,
                    class_name: class.name
                } IN $file_classes
                
                // 2. 返回类信息
                RETURN {
                    file_path: file.file_path,
                    name: class.name,
                    details: {
                        source_code: class.source_code,
                        docstring: class.docstring
                    }
                } as result
                ORDER BY file.file_path, class.name
            """, {
                'project_id': project_id,
                'file_classes': [
                    {
                        'file_path': os.path.normpath(item.file_path),  # 直接访问 Pydantic 模型属性
                        'class_name': item.class_name
                    }
                    for item in file_classes
                ]
            })
            
            records = list(result)
            return [record['result'] for record in records]
