import logging
from app.infrastructure.vector_store import VECTOR_STORE_CONN

EMBEDDING_BATCH_SIZE = 16

async def get_function_vector_space(repo_id: str, vector_size: int) -> str:
    """获取函数向量空间名称，如果不存在则创建
    
    Args:
        repo_id: 代码仓ID
        vector_size: 向量维度大小
        
    Returns:
        向量空间名称
    """
    space_name = f"repo_{repo_id}_function"
    created = await VECTOR_STORE_CONN.create_space(space_name, vector_size=vector_size)
    if not created:
        logging.error(f"创建向量空间失败: {space_name}")
    return space_name

async def get_class_vector_space(repo_id: str, vector_size: int) -> str:
    """获取类向量空间名称，如果不存在则创建
    
    Args:
        repo_id: 代码仓ID
        vector_size: 向量维度大小
        
    Returns:
        向量空间名称
    """
    space_name = f"repo_{repo_id}_class"
    created = await VECTOR_STORE_CONN.create_space(space_name, vector_size=vector_size)
    if not created:
        logging.error(f"创建向量空间失败: {space_name}")
    return space_name

async def get_chunk_source_vector_space(repo_id: str, vector_size: int) -> str:
    """获取代码片段源码向量空间名称，如果不存在则创建
    
    Args:
        repo_id: 代码仓ID
        vector_size: 向量维度大小
        
    Returns:
        向量空间名称
    """
    space_name = f"repo_{repo_id}_chunk_source"
    created = await VECTOR_STORE_CONN.create_space(space_name, vector_size=vector_size)
    if not created:
        logging.error(f"创建向量空间失败: {space_name}")
    return space_name

async def get_chunk_summary_vector_space(repo_id: str, vector_size: int) -> str:
    """获取代码片段功能说明向量空间名称，如果不存在则创建
    
    Args:
        repo_id: 代码仓ID
        vector_size: 向量维度大小
        
    Returns:
        向量空间名称
    """
    space_name = f"repo_{repo_id}_chunk_summary"
    created = await VECTOR_STORE_CONN.create_space(space_name, vector_size=vector_size)
    if not created:
        logging.error(f"创建向量空间失败: {space_name}")
    return space_name

