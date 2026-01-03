"""Obsidian Exporter for knowledge atoms."""

import io
import os
import re
import tempfile
import zipfile
from typing import List, Dict

from ..models import KnowledgeAtom, ExportResult
from .base import BaseExporter


class ObsidianExporter(BaseExporter):
    """Obsidian 知识库导出器 - 生成 Markdown 文件并打包为 ZIP"""
    
    def export(self, atoms: List[KnowledgeAtom], output_path: str = None) -> ExportResult:
        """生成 Obsidian Markdown 文件并打包为 ZIP
        
        Args:
            atoms: List of KnowledgeAtom objects to export
            output_path: Optional output ZIP file path. If None, creates a temp file.
            
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
            # Build atom lookup maps
            atom_map = {atom.id: atom for atom in atoms}
            
            # Determine output path
            if output_path is None:
                fd, output_path = tempfile.mkstemp(suffix='.zip')
                os.close(fd)
            
            # Create ZIP file
            used_filenames = set()
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for atom in atoms:
                    # Generate markdown content
                    markdown = self._generate_markdown(atom, atoms, atom_map)
                    
                    # Create safe filename with deduplication
                    base_filename = self._safe_filename(atom.title)
                    filename = base_filename + '.md'
                    
                    # Handle duplicate filenames by appending atom id suffix
                    if filename in used_filenames:
                        # Use first 8 chars of UUID to make unique
                        filename = f"{base_filename}_{atom.id[:8]}.md"
                    
                    used_filenames.add(filename)
                    
                    # Add to ZIP
                    zf.writestr(filename, markdown.encode('utf-8'))
            
            return ExportResult(
                success=True,
                message=f"成功导出 {len(atoms)} 个知识原子到 Obsidian 格式",
                exported_count=len(atoms),
                file_path=output_path
            )
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"Obsidian 导出失败: {str(e)}",
                exported_count=0,
                file_path=None
            )
    
    def _generate_markdown(
        self, 
        atom: KnowledgeAtom, 
        all_atoms: List[KnowledgeAtom],
        atom_map: Dict[str, KnowledgeAtom]
    ) -> str:
        """生成单个 Markdown 文件内容
        
        Args:
            atom: The KnowledgeAtom to generate markdown for
            all_atoms: All atoms (for finding children)
            atom_map: Map of id -> atom for quick lookup
            
        Returns:
            Complete markdown file content
        """
        parts = []
        
        # Add frontmatter
        parts.append(self._generate_frontmatter(atom, atom_map))
        
        # Add title
        parts.append(f"# {atom.title}\n")
        
        # Add content
        if atom.content:
            parts.append(atom.content)
            parts.append("")
        
        # Add backlinks
        backlinks = self._generate_backlinks(atom, all_atoms, atom_map)
        if backlinks:
            parts.append(backlinks)
        
        return '\n'.join(parts)
    
    def _generate_frontmatter(
        self, 
        atom: KnowledgeAtom,
        atom_map: Dict[str, KnowledgeAtom]
    ) -> str:
        """生成 YAML front matter
        
        Args:
            atom: The KnowledgeAtom
            atom_map: Map of id -> atom for quick lookup
            
        Returns:
            YAML frontmatter string
        """
        lines = ['---']
        lines.append(f'title: "{self._escape_yaml(atom.title)}"')
        lines.append(f'level: {atom.level}')
        
        if atom.parent_id and atom.parent_id in atom_map:
            parent = atom_map[atom.parent_id]
            lines.append(f'parent: "[[{self._escape_yaml(parent.title)}]]"')
        
        lines.append(f'source: "{self._escape_yaml(atom.source_file)}"')
        
        if atom.path:
            lines.append(f'path: "{self._escape_yaml(atom.path)}"')
        
        lines.append('---')
        lines.append('')
        
        return '\n'.join(lines)
    
    def _generate_backlinks(
        self, 
        atom: KnowledgeAtom, 
        all_atoms: List[KnowledgeAtom],
        atom_map: Dict[str, KnowledgeAtom]
    ) -> str:
        """生成双向链接
        
        Args:
            atom: The KnowledgeAtom
            all_atoms: All atoms for finding children
            atom_map: Map of id -> atom for quick lookup
            
        Returns:
            Backlinks section string
        """
        parts = []
        
        # Parent link
        if atom.parent_id and atom.parent_id in atom_map:
            parent = atom_map[atom.parent_id]
            parts.append(f"## 父节点\n")
            parts.append(f"- [[{parent.title}]]")
            parts.append("")
        
        # Children links
        children = [a for a in all_atoms if a.parent_id == atom.id]
        if children:
            parts.append(f"## 子节点\n")
            for child in children:
                parts.append(f"- [[{child.title}]]")
            parts.append("")
        
        return '\n'.join(parts)
    
    def _safe_filename(self, title: str) -> str:
        """Convert title to safe filename.
        
        Args:
            title: Original title
            
        Returns:
            Safe filename (without extension)
        """
        # Remove or replace invalid characters
        safe = re.sub(r'[<>:"/\\|?*]', '_', title)
        # Limit length
        if len(safe) > 100:
            safe = safe[:100]
        return safe.strip() or 'untitled'
    
    def _escape_yaml(self, value: str) -> str:
        """Escape string for YAML.
        
        Args:
            value: Original string
            
        Returns:
            Escaped string safe for YAML
        """
        # Escape quotes and backslashes
        return value.replace('\\', '\\\\').replace('"', '\\"')
    
    @staticmethod
    def read_zip_contents(zip_path: str) -> Dict[str, str]:
        """Read all markdown files from a ZIP.
        
        Args:
            zip_path: Path to ZIP file
            
        Returns:
            Dict mapping filename to content
        """
        contents = {}
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                if name.endswith('.md'):
                    contents[name] = zf.read(name).decode('utf-8')
        return contents
