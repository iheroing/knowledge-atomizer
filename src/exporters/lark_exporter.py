"""Lark (Feishu) Bitable Exporter for knowledge atoms."""

import time
from typing import List, Dict, Optional

import requests

from ..models import KnowledgeAtom, ExportResult
from .base import BaseExporter


class LarkAPIError(Exception):
    """飞书 API 错误"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"飞书 API 错误 ({code}): {message}")


class AuthenticationError(LarkAPIError):
    """认证错误 - App ID/Secret 无效"""
    pass


class PermissionError(LarkAPIError):
    """权限错误 - 无权限访问多维表格"""
    pass


class RateLimitError(LarkAPIError):
    """频率限制错误"""
    pass


class NetworkError(Exception):
    """网络连接错误"""
    pass


class LarkClient:
    """飞书 API 客户端"""
    
    BASE_URL = "https://open.feishu.cn/open-apis"
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    BATCH_SIZE = 500  # 飞书批量创建记录的最大数量
    
    def __init__(self, app_id: str, app_secret: str):
        """初始化飞书客户端
        
        Args:
            app_id: 飞书应用 App ID
            app_secret: 飞书应用 App Secret
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
    
    def get_access_token(self) -> str:
        """获取 tenant_access_token
        
        Returns:
            Access token string
            
        Raises:
            AuthenticationError: If credentials are invalid
            NetworkError: If network request fails
        """
        # Check if we have a valid cached token
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        
        url = f"{self.BASE_URL}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"网络请求失败: {str(e)}")
        
        if data.get("code") != 0:
            code = data.get("code", -1)
            msg = data.get("msg", "未知错误")
            
            if code in [10003, 10014]:  # Invalid app_id or app_secret
                raise AuthenticationError(
                    code,
                    f"App ID 或 App Secret 无效。请检查配置。\n"
                    f"配置指引: https://open.feishu.cn/document/home/introduction-to-custom-app-development/self-built-application-development-process"
                )
            raise LarkAPIError(code, msg)
        
        self._access_token = data.get("tenant_access_token")
        # Token expires in 2 hours, we refresh 5 minutes early
        expire = data.get("expire", 7200)
        self._token_expires_at = time.time() + expire - 300
        
        return self._access_token
    
    def batch_create_records(
        self, 
        app_token: str, 
        table_id: str, 
        records: List[dict]
    ) -> dict:
        """批量创建记录，支持自动重试
        
        Args:
            app_token: 多维表格 app_token
            table_id: 数据表 table_id
            records: 记录列表，每条记录是 {"fields": {...}} 格式
            
        Returns:
            API response dict
            
        Raises:
            PermissionError: If no permission to access the table
            RateLimitError: If rate limited
            NetworkError: If network request fails after retries
            LarkAPIError: For other API errors
        """
        url = f"{self.BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
        
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"records": records}
        
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.post(
                    url, 
                    json=payload, 
                    headers=headers, 
                    timeout=60
                )
                response.raise_for_status()
                data = response.json()
                
                code = data.get("code", 0)
                if code == 0:
                    return data
                
                msg = data.get("msg", "未知错误")
                
                # Handle specific error codes
                if code in [1254040, 1254041]:  # Permission denied
                    raise PermissionError(
                        code,
                        f"无权限访问多维表格。请确保:\n"
                        f"1. 应用已添加多维表格权限\n"
                        f"2. 多维表格已授权给应用\n"
                        f"配置步骤: https://open.feishu.cn/document/server-docs/docs/bitable-v1/notification"
                    )
                elif code == 99991400:  # Rate limit
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue
                    raise RateLimitError(code, "API 调用频率超限，请稍后重试")
                else:
                    raise LarkAPIError(code, msg)
                    
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
                raise NetworkError(
                    f"网络请求失败 (已重试 {self.MAX_RETRIES} 次): {str(e)}\n"
                    f"请检查网络连接是否正常。"
                )
        
        raise NetworkError(f"请求失败: {str(last_error)}")


class LarkExporter(BaseExporter):
    """飞书多维表格导出器"""
    
    # 字段映射: KnowledgeAtom 字段 -> 飞书字段名
    FIELD_MAPPING = {
        'id': '原子ID',
        'title': '标题',
        'content': '内容',
        'level': '层级',
        'parent_title': '父节点',
        'source_file': '来源文件',
        'path': '知识路径'
    }
    
    def __init__(
        self, 
        app_id: str, 
        app_secret: str, 
        app_token: str, 
        table_id: str
    ):
        """初始化飞书导出器
        
        Args:
            app_id: 飞书应用 App ID
            app_secret: 飞书应用 App Secret
            app_token: 多维表格 app_token (从 URL 获取)
            table_id: 数据表 table_id
        """
        self.client = LarkClient(app_id, app_secret)
        self.app_token = app_token
        self.table_id = table_id
    
    def export(self, atoms: List[KnowledgeAtom]) -> ExportResult:
        """批量写入飞书多维表格
        
        Args:
            atoms: List of KnowledgeAtom objects to export
            
        Returns:
            ExportResult with success status and count
        """
        if not atoms:
            return ExportResult(
                success=True,
                message="没有知识原子需要导出",
                exported_count=0,
                file_path=None
            )
        
        try:
            # Convert atoms to Lark records
            records = [self._convert_to_lark_record(atom) for atom in atoms]
            
            # Batch create in chunks
            total_created = 0
            for i in range(0, len(records), LarkClient.BATCH_SIZE):
                batch = records[i:i + LarkClient.BATCH_SIZE]
                result = self.client.batch_create_records(
                    self.app_token, 
                    self.table_id, 
                    batch
                )
                
                # Count created records
                created = result.get("data", {}).get("records", [])
                total_created += len(created)
            
            return ExportResult(
                success=True,
                message=f"成功写入 {total_created} 条记录到飞书多维表格",
                exported_count=total_created,
                file_path=None
            )
            
        except AuthenticationError as e:
            return ExportResult(
                success=False,
                message=str(e),
                exported_count=0,
                file_path=None
            )
        except PermissionError as e:
            return ExportResult(
                success=False,
                message=str(e),
                exported_count=0,
                file_path=None
            )
        except RateLimitError as e:
            return ExportResult(
                success=False,
                message=str(e),
                exported_count=0,
                file_path=None
            )
        except NetworkError as e:
            return ExportResult(
                success=False,
                message=str(e),
                exported_count=0,
                file_path=None
            )
        except LarkAPIError as e:
            return ExportResult(
                success=False,
                message=f"飞书 API 错误: {e.message}",
                exported_count=0,
                file_path=None
            )
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"导出失败: {str(e)}",
                exported_count=0,
                file_path=None
            )
    
    def _convert_to_lark_record(self, atom: KnowledgeAtom) -> dict:
        """将知识原子转换为飞书记录格式
        
        Args:
            atom: KnowledgeAtom object
            
        Returns:
            Dict in Lark record format {"fields": {...}}
        """
        # 注意：所有字段都转为字符串，避免类型转换错误
        # 如果飞书表格中"层级"是数字类型，则保持为 int
        fields = {
            self.FIELD_MAPPING['id']: str(atom.id),
            self.FIELD_MAPPING['title']: str(atom.title),
            self.FIELD_MAPPING['content']: str(atom.content or ''),
            self.FIELD_MAPPING['level']: atom.level,  # 数字类型保持为 int
            self.FIELD_MAPPING['parent_title']: str(atom.parent_title or ''),
            self.FIELD_MAPPING['source_file']: str(atom.source_file),
            self.FIELD_MAPPING['path']: str(atom.path or '')
        }
        
        return {"fields": fields}
