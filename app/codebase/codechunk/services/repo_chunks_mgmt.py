import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.codebase.codechunk.models.model import RepoCodeChunks
from app.codebase.codechunk.schemes.scheme import CodeChunkCreate, CodeChunkUpdate, SearchResponse, SearchResult, SearchRequest as SearchRequestDto
from app.codebase.codechunk.constants import get_chunk_source_vector_space, get_chunk_summary_vector_space
from app.codebase.codesummary.services.code_summary import CodeSummary
from app.codebase.codesummary.models.model import ContentType
from app.infrastructure.llms import embedding_factory
from app.infrastructure.vector_store import VECTOR_STORE_CONN, SearchRequest, MatchDenseExpr
import numpy as np


class RepoCodeChunksMgmt:
    """管理代码片段数据表及对应内容的向量化"""
    
    def __init__(self, db_session: AsyncSession, repo_id: Optional[str] = None):
        self.db_session = db_session
        self.repo_id = repo_id
    
    async def create(self, data: CodeChunkCreate) -> RepoCodeChunks:
        """创建代码片段数据记录"""
        try:
            chunk_data = RepoCodeChunks(
                repo_id=data.repo_id,
                source_code=data.source_code,
                file_path=data.file_path,
                start_line=data.start_line,
                end_line=data.end_line,
                summary=None,
                is_summarized=False,
                is_source_vectorized=False,
                is_summary_vectorized=False
            )
            self.db_session.add(chunk_data)
            await self.db_session.commit()
            await self.db_session.refresh(chunk_data)
            return chunk_data
        except Exception as e:
            await self.db_session.rollback()
            logging.error(f"创建代码片段数据失败: {e}")
            raise
    
    async def get_by_id(self, id: str) -> Optional[RepoCodeChunks]:
        """根据ID获取代码片段数据"""
        try:
            result = await self.db_session.execute(
                select(RepoCodeChunks).where(RepoCodeChunks.id == id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logging.error(f"获取代码片段数据失败: {e}")
            return None
    
    async def get_by_repo_id(self, repo_id: str, limit: int = 100, offset: int = 0) -> List[RepoCodeChunks]:
        """根据代码仓ID获取代码片段数据列表"""
        try:
            result = await self.db_session.execute(
                select(RepoCodeChunks)
                .where(RepoCodeChunks.repo_id == repo_id)
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
        except Exception as e:
            logging.error(f"获取代码片段数据列表失败: {e}")
            return []
    
    async def get_source_unvectorized(self, limit: int = 100) -> List[RepoCodeChunks]:
        """获取未向量化源码的代码片段数据"""
        try:
            if not self.repo_id:
                logging.error("repo_id不能为空")
                return []
            query = select(RepoCodeChunks).where(
                RepoCodeChunks.is_source_vectorized == False,
                RepoCodeChunks.repo_id == self.repo_id
            )
            query = query.limit(limit)
            result = await self.db_session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logging.error(f"获取未向量化源码的代码片段数据失败: {e}")
            return []
    
    async def get_summary_unvectorized(self, limit: int = 100) -> List[RepoCodeChunks]:
        """获取未向量化功能说明的代码片段数据"""
        try:
            if not self.repo_id:
                logging.error("repo_id不能为空")
                return []
            query = select(RepoCodeChunks).where(
                RepoCodeChunks.is_summary_vectorized == False,
                RepoCodeChunks.is_summarized == True,
                RepoCodeChunks.repo_id == self.repo_id
            )
            query = query.limit(limit)
            result = await self.db_session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logging.error(f"获取未向量化功能说明的代码片段数据失败: {e}")
            return []
    
    async def get_unsummarized(self, limit: int = 100) -> List[RepoCodeChunks]:
        """获取未生成summary的代码片段数据"""
        try:
            if not self.repo_id:
                logging.error("repo_id不能为空")
                return []
            query = select(RepoCodeChunks).where(
                RepoCodeChunks.is_summarized == False,
                RepoCodeChunks.repo_id == self.repo_id
            )
            query = query.limit(limit)
            result = await self.db_session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logging.error(f"获取未生成summary的代码片段数据失败: {e}")
            return []
    
    async def update(self, id: str, data: CodeChunkUpdate) -> Optional[RepoCodeChunks]:
        """更新代码片段数据"""
        try:
            chunk_data = await self.get_by_id(id)
            if not chunk_data:
                return None
            
            if data.summary is not None:
                chunk_data.summary = data.summary
            if data.is_summarized is not None:
                chunk_data.is_summarized = data.is_summarized
            if data.is_source_vectorized is not None:
                chunk_data.is_source_vectorized = data.is_source_vectorized
            if data.is_summary_vectorized is not None:
                chunk_data.is_summary_vectorized = data.is_summary_vectorized
            if data.source_vector_id is not None:
                chunk_data.source_vector_id = data.source_vector_id
            if data.summary_vector_id is not None:
                chunk_data.summary_vector_id = data.summary_vector_id
            
            await self.db_session.commit()
            await self.db_session.refresh(chunk_data)
            return chunk_data
        except Exception as e:
            await self.db_session.rollback()
            logging.error(f"更新代码片段数据失败: {e}")
            return None
    
    async def delete(self, id: str) -> bool:
        """删除代码片段数据"""
        try:
            chunk_data = await self.get_by_id(id)
            if not chunk_data:
                return False
            
            await self.db_session.delete(chunk_data)
            await self.db_session.commit()
            return True
        except Exception as e:
            await self.db_session.rollback()
            logging.error(f"删除代码片段数据失败: {e}")
            return False
    
    async def generate_summary(self, chunk_data: RepoCodeChunks) -> str:
        """生成代码片段功能描述"""
        try:
            summary = await CodeSummary.llm_summarize(
                chunk_data.source_code,
                ContentType.FRAGMENT
            )
            return summary
        except Exception as e:
            logging.error(f"生成代码片段摘要失败: {e}")
            return ""
    
    async def vectorize_source(self, chunk_data: RepoCodeChunks) -> bool:
        """向量化代码片段源码"""
        try:
            if chunk_data.is_source_vectorized and chunk_data.source_vector_id:
                return True
            
            embedding_model = embedding_factory.create_model()
            if not embedding_model:
                logging.error("无法创建嵌入模型")
                return False
            
            vectors, _ = await embedding_model.encode([chunk_data.source_code])
            if vectors is None or len(vectors) == 0:
                logging.error("向量化失败")
                return False
            
            vector = vectors[0].tolist()
            
            record = {
                "id": chunk_data.id,
                "repo_id": chunk_data.repo_id,
                "source_code": chunk_data.source_code,
                "file_path": chunk_data.file_path,
                "start_line": chunk_data.start_line,
                "end_line": chunk_data.end_line,
                "summary": chunk_data.summary,
                "vector": vector
            }
            
            space_name = get_chunk_source_vector_space(chunk_data.repo_id)
            created = await VECTOR_STORE_CONN.create_space(space_name, vector_size=len(vector))
            if not created:
                logging.error(f"创建向量空间失败: {space_name}")
                return False
            vector_ids = await VECTOR_STORE_CONN.insert_records(space_name, [record])
            if vector_ids and len(vector_ids) > 0:
                await self.update(chunk_data.id, CodeChunkUpdate(
                    is_source_vectorized=True,
                    source_vector_id=vector_ids[0]
                ))
                return True
            return False
        except Exception as e:
            logging.error(f"向量化代码片段源码失败: {e}")
            return False
    
    async def vectorize_summary(self, chunk_data: RepoCodeChunks) -> bool:
        """向量化代码片段功能说明"""
        try:
            if chunk_data.is_summary_vectorized and chunk_data.summary_vector_id:
                return True
            
            if not chunk_data.summary:
                logging.error("功能说明为空，无法向量化")
                return False
            
            embedding_model = embedding_factory.create_model()
            if not embedding_model:
                logging.error("无法创建嵌入模型")
                return False
            
            vectors, _ = await embedding_model.encode([chunk_data.summary])
            if vectors is None or len(vectors) == 0:
                logging.error("向量化失败")
                return False
            
            vector = vectors[0].tolist()
            
            record = {
                "id": chunk_data.id,
                "repo_id": chunk_data.repo_id,
                "source_code": chunk_data.source_code,
                "file_path": chunk_data.file_path,
                "start_line": chunk_data.start_line,
                "end_line": chunk_data.end_line,
                "summary": chunk_data.summary,
                "vector": vector
            }
            
            space_name = get_chunk_summary_vector_space(chunk_data.repo_id)
            created = await VECTOR_STORE_CONN.create_space(space_name, vector_size=len(vector))
            if not created:
                logging.error(f"创建向量空间失败: {space_name}")
                return False
            vector_ids = await VECTOR_STORE_CONN.insert_records(space_name, [record])
            if vector_ids and len(vector_ids) > 0:
                await self.update(chunk_data.id, CodeChunkUpdate(
                    is_summary_vectorized=True,
                    summary_vector_id=vector_ids[0]
                ))
                return True
            return False
        except Exception as e:
            logging.error(f"向量化代码片段功能说明失败: {e}")
            return False
    
    async def batch_generate_summary(self, limit: int = 100) -> int:
        """批量生成代码片段功能描述"""
        try:
            unsummarized = await self.get_unsummarized(limit=limit)
            count = 0
            for chunk_data in unsummarized:
                try:
                    summary = await self.generate_summary(chunk_data)
                    if summary:
                        await self.update(chunk_data.id, CodeChunkUpdate(
                            summary=summary,
                            is_summarized=True
                        ))
                        count += 1
                except Exception as e:
                    logging.error(f"生成代码片段{chunk_data.id}摘要失败: {e}")
                    continue
            return count
        except Exception as e:
            logging.error(f"批量生成summary失败: {e}")
            return 0
    
    async def batch_vectorize_source(self, limit: int = 100) -> int:
        """批量向量化未向量化的代码片段源码"""
        try:
            unvectorized = await self.get_source_unvectorized(limit=limit)
            count = 0
            for chunk_data in unvectorized:
                if await self.vectorize_source(chunk_data):
                    count += 1
            return count
        except Exception as e:
            logging.error(f"批量向量化源码失败: {e}")
            return 0
    
    async def batch_vectorize_summary(self, limit: int = 100) -> int:
        """批量向量化未向量化的代码片段功能说明"""
        try:
            unvectorized = await self.get_summary_unvectorized(limit=limit)
            count = 0
            for chunk_data in unvectorized:
                if await self.vectorize_summary(chunk_data):
                    count += 1
            return count
        except Exception as e:
            logging.error(f"批量向量化功能说明失败: {e}")
            return 0
    
    async def search_source(self, request: SearchRequestDto) -> SearchResponse:
        """向量搜索代码片段源码"""
        try:
            repo_id = request.repo_id or self.repo_id
            if not repo_id:
                logging.error("repo_id不能为空")
                return SearchResponse(results=[], total=0)
            
            embedding_model = embedding_factory.create_model()
            if not embedding_model:
                logging.error("无法创建嵌入模型")
                return SearchResponse(results=[], total=0)
            
            query_vector, _ = await embedding_model.encode_queries(request.query)
            if query_vector is None:
                logging.error("查询向量化失败")
                return SearchResponse(results=[], total=0)
            
            vector_expr = MatchDenseExpr(
                field="vector",
                vector=query_vector.tolist(),
                top_k=request.top_k
            )
            
            search_request = SearchRequest(
                query=vector_expr,
                top_k=request.top_k
            )
            
            space_name = get_chunk_source_vector_space(repo_id)
            space_names = [space_name]
            if request.file_path:
                search_request.filter = {"term": {"file_path": request.file_path}}
            
            result = await VECTOR_STORE_CONN.search(space_names, search_request)
            
            total = VECTOR_STORE_CONN.get_total(result)
            chunk_ids = VECTOR_STORE_CONN.get_chunk_ids(result)
            fields = VECTOR_STORE_CONN.get_fields(result, ["id", "source_code", "file_path", "start_line", "end_line", "summary"])
            
            results = []
            for i, chunk_id in enumerate(chunk_ids):
                field_data = fields.get(chunk_id, {})
                results.append(SearchResult(
                    id=field_data.get("id", chunk_id),
                    source_code=field_data.get("source_code", ""),
                    file_path=field_data.get("file_path", ""),
                    start_line=field_data.get("start_line", 0),
                    end_line=field_data.get("end_line", 0),
                    summary=field_data.get("summary"),
                    score=field_data.get("_score")
                ))
            
            return SearchResponse(results=results, total=total)
        except Exception as e:
            logging.error(f"搜索代码片段源码失败: {e}")
            return SearchResponse(results=[], total=0)
    
    async def search_summary(self, request: SearchRequestDto) -> SearchResponse:
        """向量搜索代码片段功能说明"""
        try:
            repo_id = request.repo_id or self.repo_id
            if not repo_id:
                logging.error("repo_id不能为空")
                return SearchResponse(results=[], total=0)
            
            embedding_model = embedding_factory.create_model()
            if not embedding_model:
                logging.error("无法创建嵌入模型")
                return SearchResponse(results=[], total=0)
            
            query_vector, _ = await embedding_model.encode_queries(request.query)
            if query_vector is None:
                logging.error("查询向量化失败")
                return SearchResponse(results=[], total=0)
            
            vector_expr = MatchDenseExpr(
                field="vector",
                vector=query_vector.tolist(),
                top_k=request.top_k
            )
            
            search_request = SearchRequest(
                query=vector_expr,
                top_k=request.top_k
            )
            
            space_name = get_chunk_summary_vector_space(repo_id)
            space_names = [space_name]
            if request.file_path:
                search_request.filter = {"term": {"file_path": request.file_path}}
            
            result = await VECTOR_STORE_CONN.search(space_names, search_request)
            
            total = VECTOR_STORE_CONN.get_total(result)
            chunk_ids = VECTOR_STORE_CONN.get_chunk_ids(result)
            fields = VECTOR_STORE_CONN.get_fields(result, ["id", "source_code", "file_path", "start_line", "end_line", "summary"])
            
            results = []
            for i, chunk_id in enumerate(chunk_ids):
                field_data = fields.get(chunk_id, {})
                results.append(SearchResult(
                    id=field_data.get("id", chunk_id),
                    source_code=field_data.get("source_code", ""),
                    file_path=field_data.get("file_path", ""),
                    start_line=field_data.get("start_line", 0),
                    end_line=field_data.get("end_line", 0),
                    summary=field_data.get("summary"),
                    score=field_data.get("_score")
                ))
            
            return SearchResponse(results=results, total=total)
        except Exception as e:
            logging.error(f"搜索代码片段功能说明失败: {e}")
            return SearchResponse(results=[], total=0)
    
    async def text_search(self, request: SearchRequestDto) -> SearchResponse:
        """文本搜索代码片段数据"""
        try:
            repo_id = request.repo_id or self.repo_id
            if not repo_id:
                logging.error("repo_id不能为空")
                return SearchResponse(results=[], total=0)
            
            query = select(RepoCodeChunks).where(RepoCodeChunks.repo_id == repo_id)
            
            if request.file_path:
                query = query.where(RepoCodeChunks.file_path == request.file_path)
            
            if request.query:
                query = query.where(
                    (RepoCodeChunks.source_code.contains(request.query)) |
                    (RepoCodeChunks.summary.contains(request.query))
                )
            
            query = query.limit(request.top_k)
            
            result = await self.db_session.execute(query)
            chunks = list(result.scalars().all())
            
            results = [
                SearchResult(
                    id=chunk.id,
                    source_code=chunk.source_code,
                    file_path=chunk.file_path,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    summary=chunk.summary
                )
                for chunk in chunks
            ]
            
            return SearchResponse(results=results, total=len(results))
        except Exception as e:
            logging.error(f"文本搜索代码片段数据失败: {e}")
            return SearchResponse(results=[], total=0)
