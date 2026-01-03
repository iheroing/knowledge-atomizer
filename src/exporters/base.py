"""Base exporter interface."""

from abc import ABC, abstractmethod
from typing import List

from ..models import KnowledgeAtom, ExportResult


class BaseExporter(ABC):
    """导出器基类"""
    
    @abstractmethod
    def export(self, atoms: List[KnowledgeAtom]) -> ExportResult:
        """导出知识原子
        
        Args:
            atoms: List of KnowledgeAtom objects to export
            
        Returns:
            ExportResult with success status and details
        """
        pass
