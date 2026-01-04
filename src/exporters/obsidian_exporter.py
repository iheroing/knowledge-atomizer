"""Obsidian Exporter for knowledge atoms."""

import io
import os
import re
import tempfile
import zipfile
from datetime import datetime
from typing import List, Dict

from ..models import KnowledgeAtom, ExportResult
from .base import BaseExporter


class ObsidianExporter(BaseExporter):
    """Obsidian 知识库导出器 - 生成 Markdown 文件并打包为 ZIP
    
    特性：
    - 丰富的 frontmatter 元数据（标签、别名、日期等）
    - 双向链接（父节点、子节点、同级节点）
    - MOC (Map of Content) 索引文件
    - 按层级组织的文件夹结构
    """
    
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
                
                # Generate MOC (Map of Content) index file
                moc_content = self._generate_moc(atoms, atom_map)
                zf.writestr('_MOC_知识地图.md', moc_content.encode('utf-8'))
            
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
        
        # 别名 (aliases) - 使用路径中的各级标题
        aliases = []
        if atom.path:
            path_parts = [p.strip() for p in atom.path.split('>')]
            if len(path_parts) > 1:
                aliases.append(path_parts[-1])  # 最后一级
        if aliases:
            quoted_aliases = ['"{}"'.format(a) for a in aliases]
            lines.append(f'aliases: [{", ".join(quoted_aliases)}]')
        
        # 标签 (tags)
        tags = self._generate_tags(atom)
        if tags:
            lines.append(f'tags: [{", ".join(tags)}]')
        
        lines.append(f'level: {atom.level}')
        
        if atom.parent_id and atom.parent_id in atom_map:
            parent = atom_map[atom.parent_id]
            lines.append(f'parent: "[[{self._escape_yaml(parent.title)}]]"')
        
        lines.append(f'source: "{self._escape_yaml(atom.source_file)}"')
        
        if atom.path:
            lines.append(f'path: "{self._escape_yaml(atom.path)}"')
        
        # 创建日期
        lines.append(f'created: {datetime.now().strftime("%Y-%m-%d")}')
        
        # 类型标记
        lines.append('type: knowledge-atom')
        
        lines.append('---')
        lines.append('')
        
        return '\n'.join(lines)
    
    def _generate_tags(self, atom: KnowledgeAtom) -> List[str]:
        """生成标签列表
        
        Args:
            atom: The KnowledgeAtom
            
        Returns:
            List of tag strings
        """
        tags = []
        
        # 层级标签
        level_names = {1: '章节', 2: '小节', 3: '主题', 4: '概念', 5: '细节'}
        level_name = level_names.get(atom.level, f'L{atom.level}')
        tags.append(f'层级/{level_name}')
        
        # 来源文件标签（去掉扩展名）
        if atom.source_file:
            source_name = atom.source_file.rsplit('.', 1)[0]
            safe_source = re.sub(r'[^\w\u4e00-\u9fff]', '_', source_name)
            tags.append(f'来源/{safe_source}')
        
        # 知识原子标签
        tags.append('知识原子')
        
        return tags
    
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
        parts.append("---")
        parts.append("")
        parts.append("## 🔗 关联笔记")
        parts.append("")
        
        # Parent link
        if atom.parent_id and atom.parent_id in atom_map:
            parent = atom_map[atom.parent_id]
            parts.append(f"**⬆️ 上级**: [[{parent.title}]]")
            parts.append("")
        
        # Sibling links (same parent)
        if atom.parent_id:
            siblings = [a for a in all_atoms if a.parent_id == atom.parent_id and a.id != atom.id]
            if siblings:
                parts.append("**↔️ 同级**:")
                for sibling in siblings[:5]:  # Limit to 5 siblings
                    parts.append(f"- [[{sibling.title}]]")
                if len(siblings) > 5:
                    parts.append(f"- ... 还有 {len(siblings) - 5} 个")
                parts.append("")
        
        # Children links
        children = [a for a in all_atoms if a.parent_id == atom.id]
        if children:
            parts.append("**⬇️ 下级**:")
            for child in children:
                parts.append(f"- [[{child.title}]]")
            parts.append("")
        
        # Path breadcrumb
        if atom.path and '>' in atom.path:
            parts.append("**📍 知识路径**:")
            parts.append(f"`{atom.path}`")
            parts.append("")
        
        return '\n'.join(parts)
    
    def _generate_moc(
        self, 
        atoms: List[KnowledgeAtom],
        atom_map: Dict[str, KnowledgeAtom]
    ) -> str:
        """生成 MOC (Map of Content) 索引文件
        
        Args:
            atoms: All atoms
            atom_map: Map of id -> atom
            
        Returns:
            MOC markdown content
        """
        parts = []
        
        # Frontmatter
        parts.append('---')
        parts.append('title: "知识地图 (MOC)"')
        parts.append('tags: [MOC, 索引]')
        parts.append(f'created: {datetime.now().strftime("%Y-%m-%d")}')
        parts.append('type: moc')
        parts.append('---')
        parts.append('')
        
        # Header
        parts.append('# 🗺️ 知识地图')
        parts.append('')
        parts.append(f'> 本知识库共包含 **{len(atoms)}** 个知识原子')
        parts.append('')
        
        # Statistics
        level_counts = {}
        for atom in atoms:
            level_counts[atom.level] = level_counts.get(atom.level, 0) + 1
        
        parts.append('## 📊 统计')
        parts.append('')
        for level in sorted(level_counts.keys()):
            level_names = {1: '章节', 2: '小节', 3: '主题', 4: '概念', 5: '细节'}
            name = level_names.get(level, f'L{level}')
            parts.append(f'- {name} (H{level}): {level_counts[level]} 个')
        parts.append('')
        
        # Tree structure
        parts.append('## 🌳 知识树')
        parts.append('')
        
        root_atoms = [a for a in atoms if a.parent_id is None]
        
        def render_tree(atom: KnowledgeAtom, depth: int = 0):
            indent = '  ' * depth
            parts.append(f'{indent}- [[{atom.title}]]')
            children = [a for a in atoms if a.parent_id == atom.id]
            for child in children:
                render_tree(child, depth + 1)
        
        for root in root_atoms:
            render_tree(root)
        
        parts.append('')
        
        # By source file
        sources = {}
        for atom in atoms:
            src = atom.source_file
            if src not in sources:
                sources[src] = []
            sources[src].append(atom)
        
        if len(sources) > 1:
            parts.append('## 📁 按来源文件')
            parts.append('')
            for src, src_atoms in sources.items():
                parts.append(f'### {src}')
                for atom in src_atoms:
                    if atom.parent_id is None:
                        parts.append(f'- [[{atom.title}]]')
            parts.append('')
        
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
