EMBEDDING_BATCH_SIZE = 16

def get_function_vector_space(repo_id: str) -> str:
    """获取函数向量空间名称"""
    return f"repo_{repo_id}_function"

def get_class_vector_space(repo_id: str) -> str:
    """获取类向量空间名称"""
    return f"repo_{repo_id}_class"

def get_chunk_source_vector_space(repo_id: str) -> str:
    """获取代码片段源码向量空间名称"""
    return f"repo_{repo_id}_chunk_source"

def get_chunk_summary_vector_space(repo_id: str) -> str:
    """获取代码片段功能说明向量空间名称"""
    return f"repo_{repo_id}_chunk_summary"

