"""JSON Exporter for knowledge atoms."""

import json
import os
import tempfile
from datetime import datetime
from typing import List, Dict, Any

from ..models import KnowledgeAtom, ExportResult
from .base import BaseExporter


class JSONExporter(BaseExporter):
    """JSON 导出器 - 生成结构化 JSON 文件
    
    支持两种格式：
    - flat: 扁平列表格式
    - tree: 树形嵌套格式
    """
    
    def export(
        self, 
        atoms: List[KnowledgeAtom], 
        output_path: str = None,
        format: str = "flat"
    ) -> ExportResult:
        """生成 JSON 文件
        
        Args:
            atoms: List of KnowledgeAtom objects to export
            output_path: Optional output file path
            format: "flat" for list format, "tree" for nested format
            
        Returns:
            ExportResult with success status and file path
        """
        if not atoms:
            return ExportResult(
                success=True,
                message="没有知识原子需要导出",
                exported_count=0,
                file_path=None
            )
        
        try:
            # Generate JSON content
            if format == "tree":
                data = self._generate_tree_format(atoms)
            else:
                data = self._generate_flat_format(atoms)
            
            json_content = json.dumps(data, ensure_ascii=False, indent=2)
            
            # Determine output path
            if output_path is None:
                fd, output_path = tempfile.mkstemp(suffix='.json')
                os.close(fd)
            
            # Write file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_content)
            
            return ExportResult(
                success=True,
                message=f"成功导出 {len(atoms)} 个知识原子到 JSON",
                exported_count=len(atoms),
                file_path=output_path
            )
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"JSON 导出失败: {str(e)}",
                exported_count=0,
                file_path=None
            )
    
    def _generate_flat_format(self, atoms: List[KnowledgeAtom]) -> Dict[str, Any]:
        """Generate flat list format.
        
        Args:
            atoms: List of KnowledgeAtom objects
            
        Returns:
            Dict with metadata and atoms list
        """
        # Collect unique sources
        sources = list(set(a.source_file for a in atoms))
        
        return {
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "total_count": len(atoms),
                "sources": sources,
                "format": "flat"
            },
            "atoms": [self._atom_to_dict(a) for a in atoms]
        }
    
    def _generate_tree_format(self, atoms: List[KnowledgeAtom]) -> Dict[str, Any]:
        """Generate tree nested format.
        
        Args:
            atoms: List of KnowledgeAtom objects
            
        Returns:
            Dict with metadata and nested tree structure
        """
        # Build atom map
        atom_map = {a.id: a for a in atoms}
        
        # Find root atoms
        roots = [a for a in atoms if a.parent_id is None]
        
        # Build tree recursively
        def build_node(atom: KnowledgeAtom) -> Dict[str, Any]:
            node = self._atom_to_dict(atom)
            children = [a for a in atoms if a.parent_id == atom.id]
            if children:
                node["children"] = [build_node(c) for c in children]
            return node
        
        tree = [build_node(r) for r in roots]
        
        # Collect unique sources
        sources = list(set(a.source_file for a in atoms))
        
        return {
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "total_count": len(atoms),
                "sources": sources,
                "format": "tree"
            },
            "tree": tree
        }
    
    def _atom_to_dict(self, atom: KnowledgeAtom) -> Dict[str, Any]:
        """Convert KnowledgeAtom to dict.
        
        Args:
            atom: KnowledgeAtom object
            
        Returns:
            Dict representation
        """
        return {
            "id": atom.id,
            "title": atom.title,
            "content": atom.content or "",
            "level": atom.level,
            "parent_id": atom.parent_id,
            "parent_title": atom.parent_title or "",
            "source_file": atom.source_file,
            "path": atom.path or ""
        }
