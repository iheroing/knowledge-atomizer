"""Streamlit Web UI for Knowledge Atomizer."""

import os
import sys
import tempfile
from typing import List, Optional

import streamlit as st

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import KnowledgeAtom
from src.parser import DocumentParser, ParserError
from src.markdown_parser import MarkdownParser
from src.transformer import KnowledgeTransformer
from src.statistics import compute_statistics
from src.exporters.csv_exporter import CSVExporter
from src.exporters.obsidian_exporter import ObsidianExporter
from src.exporters.lark_exporter import LarkExporter


class KnowledgeAtomizerApp:
    """Streamlit Web 应用"""
    
    def __init__(self):
        """初始化应用"""
        self.docx_parser = DocumentParser()
        self.md_parser = MarkdownParser()
        self.transformer = KnowledgeTransformer()
    
    def run(self):
        """运行应用"""
        st.set_page_config(
            page_title="Knowledge Atomizer - 知识原子化中台",
            page_icon="🧬",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Custom CSS for better styling
        st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        .sub-header {
            color: #666;
            font-size: 1.1rem;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1rem;
            border-radius: 10px;
            color: white;
            text-align: center;
        }
        .tree-node {
            padding: 0.5rem;
            margin: 0.25rem 0;
            border-left: 3px solid #667eea;
            background: #f8f9fa;
            border-radius: 0 5px 5px 0;
        }
        .path-badge {
            background: #e9ecef;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            color: #495057;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Header
        st.markdown('<p class="main-header">🧬 Knowledge Atomizer</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">知识原子化中台 - 将 Word/Markdown 文档转换为结构化知识原子，支持飞书多维表格和 Obsidian</p>', unsafe_allow_html=True)
        
        # Initialize session state
        if 'atoms' not in st.session_state:
            st.session_state.atoms = None
        if 'source_file' not in st.session_state:
            st.session_state.source_file = None
        if 'source_files' not in st.session_state:
            st.session_state.source_files = []
        if 'selected_atom' not in st.session_state:
            st.session_state.selected_atom = None
        if 'csv_data' not in st.session_state:
            st.session_state.csv_data = None
        if 'zip_data' not in st.session_state:
            st.session_state.zip_data = None
        
        # Sidebar for upload and stats
        with st.sidebar:
            self._render_sidebar()
        
        # Main content
        if st.session_state.atoms:
            self._render_main_content(st.session_state.atoms)
        else:
            self._render_welcome()
    
    def _render_sidebar(self):
        """渲染侧边栏"""
        st.header("📤 上传文档")
        
        uploaded_files = st.file_uploader(
            "选择文档（支持多选）",
            type=['docx', 'md'],
            accept_multiple_files=True,
            help="支持 .docx (Word) 和 .md (Markdown) 格式"
        )
        
        if uploaded_files:
            st.caption(f"已选择 {len(uploaded_files)} 个文件")
            for f in uploaded_files:
                file_icon = "📄" if f.name.endswith('.docx') else "📝"
                st.text(f"{file_icon} {f.name}")
            
            if st.button("🚀 开始解析", use_container_width=True, type="primary"):
                self._process_files(uploaded_files)
        
        # Show stats if atoms exist
        if st.session_state.atoms:
            st.divider()
            st.header("📊 统计信息")
            stats = compute_statistics(st.session_state.atoms)
            
            st.metric("📚 知识原子总数", stats.total_count)
            
            st.markdown("**各层级分布**")
            for level in range(1, 6):
                count = stats.level_counts.get(level, 0)
                if count > 0:
                    progress = count / stats.total_count if stats.total_count > 0 else 0
                    st.progress(progress, text=f"H{level}: {count} 个")
            
            st.divider()
            # Show source files
            if st.session_state.source_files:
                st.markdown(f"**来源文件** ({len(st.session_state.source_files)} 个):")
                for sf in st.session_state.source_files:
                    st.text(f"  • {sf}")
            else:
                st.markdown(f"**来源文件**: {st.session_state.source_file}")
            
            if st.button("🗑️ 清除数据", use_container_width=True):
                self._clear_all_data()
                st.rerun()
    
    def _process_files(self, uploaded_files):
        """处理多个上传的文件"""
        all_atoms = []
        source_files = []
        errors = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"正在解析: {uploaded_file.name}")
            progress_bar.progress((i + 1) / len(uploaded_files))
            
            try:
                atoms = self._parse_single_file(uploaded_file)
                all_atoms.extend(atoms)
                source_files.append(uploaded_file.name)
            except Exception as e:
                errors.append(f"{uploaded_file.name}: {str(e)}")
        
        progress_bar.empty()
        status_text.empty()
        
        if all_atoms:
            st.session_state.atoms = all_atoms
            st.session_state.source_files = source_files
            st.session_state.source_file = ", ".join(source_files)
            
            # Clear cached exports
            self._clear_export_cache()
            
            st.success(f"✅ 成功从 {len(source_files)} 个文件中提取 {len(all_atoms)} 个知识原子")
            
            if errors:
                st.warning(f"⚠️ {len(errors)} 个文件解析失败:\n" + "\n".join(errors))
            
            st.rerun()
        else:
            st.error("❌ 所有文件解析失败:\n" + "\n".join(errors))
    
    def _parse_single_file(self, uploaded_file) -> List[KnowledgeAtom]:
        """解析单个文件"""
        filename = uploaded_file.name
        suffix = '.md' if filename.endswith('.md') else '.docx'
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        try:
            if filename.endswith('.md'):
                # Parse Markdown
                tree = self.md_parser.parse(tmp_path)
                tree.source_file = filename
            else:
                # Parse Word
                tree = self.docx_parser.parse(tmp_path)
                tree.source_file = filename
            
            atoms = self.transformer.transform(tree)
            return atoms
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def _clear_export_cache(self):
        """清除导出缓存"""
        st.session_state.csv_data = None
        st.session_state.zip_data = None
    
    def _clear_all_data(self):
        """清除所有数据和缓存"""
        st.session_state.atoms = None
        st.session_state.source_file = None
        st.session_state.source_files = []
        st.session_state.selected_atom = None
        self._clear_export_cache()
    
    def _render_welcome(self):
        """渲染欢迎页面"""
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            ### 👋 欢迎使用 Knowledge Atomizer
            
            **功能特点：**
            - 📄 解析 Word (.docx) 和 Markdown (.md) 文档
            - 📚 支持批量上传多个文件
            - 🧬 将内容拆解为独立的知识原子
            - 🌳 可视化知识树结构
            - 📤 导出到飞书多维表格、Obsidian、CSV
            
            **使用方法：**
            1. 在左侧上传文档（支持多选）
            2. 点击"开始解析"按钮
            3. 预览知识结构
            4. 选择导出格式
            
            **支持的格式：**
            - `.docx` - Microsoft Word 文档
            - `.md` - Markdown 文档（ATX 风格标题）
            
            ---
            *请在左侧上传文档开始使用*
            """)
    
    def _render_main_content(self, atoms: List[KnowledgeAtom]):
        """渲染主内容区"""
        tab1, tab2, tab3, tab4 = st.tabs(["🌳 知识树", "📋 列表视图", "📊 可视化", "📥 导出"])
        
        with tab1:
            self._render_tree_view(atoms)
        
        with tab2:
            self._render_list_view(atoms)
        
        with tab3:
            self._render_visualization(atoms)
        
        with tab4:
            self._render_export_section(atoms)
    
    def _render_tree_view(self, atoms: List[KnowledgeAtom]):
        """渲染树形视图 - 优化版本，使用 selectbox 替代大量按钮"""
        st.subheader("🌳 知识树结构")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**选择知识原子**")
            
            # 使用 selectbox 替代大量按钮，大幅提升性能
            atom_options = []
            atom_map = {}
            
            for atom in atoms:
                level_icons = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🔵"}
                icon = level_icons.get(atom.level, "⚪")
                indent = "  " * (atom.level - 1)
                label = f"{indent}{icon} H{atom.level} | {atom.title[:40]}"
                atom_options.append(label)
                atom_map[label] = atom
            
            if atom_options:
                selected_label = st.selectbox(
                    "选择节点查看详情",
                    options=atom_options,
                    index=0,
                    label_visibility="collapsed"
                )
                
                if selected_label:
                    st.session_state.selected_atom = atom_map[selected_label]
            
            # 显示简化的树形结构（只显示前20个根节点）
            st.markdown("**层级预览**")
            root_atoms = [a for a in atoms if a.parent_id is None][:20]
            
            for root in root_atoms:
                self._render_tree_text(root, atoms, 0, max_depth=2)
            
            if len([a for a in atoms if a.parent_id is None]) > 20:
                st.caption(f"... 还有更多根节点")
        
        with col2:
            st.markdown("**详细信息**")
            if st.session_state.selected_atom:
                atom = st.session_state.selected_atom
                
                st.markdown(f"### {atom.title}")
                st.markdown(f"**完整路径**: `{atom.path}`")
                
                info_col1, info_col2 = st.columns(2)
                with info_col1:
                    st.markdown(f"**层级**: H{atom.level}")
                    st.markdown(f"**父节点**: {atom.parent_title or '(根节点)'}")
                with info_col2:
                    st.markdown(f"**ID**: `{atom.id[:8]}...`")
                    children_count = len([a for a in atoms if a.parent_id == atom.id])
                    st.markdown(f"**子节点数**: {children_count}")
                
                st.divider()
                st.markdown("**内容**")
                if atom.content:
                    st.markdown(atom.content)
                else:
                    st.caption("(无内容)")
            else:
                st.info("👈 从左侧选择节点查看详情")
    
    def _render_tree_text(self, atom: KnowledgeAtom, all_atoms: List[KnowledgeAtom], depth: int, max_depth: int = 2):
        """渲染树形文本（简化版，限制深度）"""
        if depth > max_depth:
            return
        
        indent = "　" * depth
        prefix = "├─ " if depth > 0 else ""
        level_icons = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🔵"}
        icon = level_icons.get(atom.level, "⚪")
        
        st.text(f"{indent}{prefix}{icon} {atom.title[:30]}")
        
        children = [a for a in all_atoms if a.parent_id == atom.id][:5]
        for child in children:
            self._render_tree_text(child, all_atoms, depth + 1, max_depth)
    
    def _render_list_view(self, atoms: List[KnowledgeAtom]):
        """渲染列表视图"""
        st.subheader("📋 知识原子列表")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            level_filter = st.multiselect(
                "筛选层级",
                options=[1, 2, 3, 4, 5],
                default=[1, 2, 3, 4, 5],
                format_func=lambda x: f"H{x}"
            )
        with col2:
            search_term = st.text_input("🔍 搜索标题或内容")
        with col3:
            sort_by = st.selectbox("排序", ["层级", "标题", "路径长度"])
        
        # Filter atoms
        filtered = [a for a in atoms if a.level in level_filter]
        if search_term:
            filtered = [a for a in filtered if search_term.lower() in a.title.lower() or search_term.lower() in (a.content or "").lower()]
        
        # Sort
        if sort_by == "层级":
            filtered.sort(key=lambda x: x.level)
        elif sort_by == "标题":
            filtered.sort(key=lambda x: x.title)
        else:
            filtered.sort(key=lambda x: len(x.path))
        
        st.caption(f"显示 {len(filtered)} / {len(atoms)} 个知识原子")
        
        # Display as table
        for atom in filtered:
            with st.expander(f"H{atom.level} | {atom.title}", expanded=False):
                st.markdown(f"**路径**: `{atom.path}`")
                if atom.content:
                    st.markdown(atom.content[:500] + ("..." if len(atom.content) > 500 else ""))
                else:
                    st.caption("(无内容)")
    
    def _render_visualization(self, atoms: List[KnowledgeAtom]):
        """渲染可视化图表 - 增强版，带下载功能"""
        import pandas as pd
        import json
        
        st.subheader("📊 知识结构可视化")
        
        stats = compute_statistics(atoms)
        
        # Row 1: Key metrics with styled cards
        st.markdown("""
        <style>
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.2rem;
            border-radius: 12px;
            color: white;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 2rem;
            font-weight: bold;
        }
        .metric-label {
            font-size: 0.9rem;
            opacity: 0.9;
        }
        </style>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📚 总原子数", stats.total_count)
        with col2:
            avg_content_len = sum(len(a.content or "") for a in atoms) / len(atoms) if atoms else 0
            st.metric("📝 平均内容长度", f"{avg_content_len:.0f} 字")
        with col3:
            max_depth = max((a.path.count(">") + 1 for a in atoms), default=0)
            st.metric("🌲 最大深度", f"{max_depth} 层")
        with col4:
            root_count = len([a for a in atoms if a.parent_id is None])
            st.metric("🌱 根节点数", root_count)
        
        st.divider()
        
        # Row 2: Charts with download
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📊 层级分布**")
            level_data = pd.DataFrame({
                '层级': [f'H{i}' for i in range(1, 6)],
                '数量': [stats.level_counts.get(i, 0) for i in range(1, 6)]
            })
            st.bar_chart(level_data.set_index('层级'))
            # 下载层级分布数据
            st.download_button(
                "⬇️ 下载层级数据",
                data=level_data.to_csv(index=False).encode('utf-8-sig'),
                file_name="层级分布.csv",
                mime="text/csv",
                key="dl_level"
            )
        
        with col2:
            st.markdown("**📏 内容长度分布**")
            lengths = [len(a.content or "") for a in atoms]
            buckets = {'0': 0, '1-100': 0, '101-500': 0, '501-1000': 0, '1000+': 0}
            for l in lengths:
                if l == 0:
                    buckets['0'] += 1
                elif l <= 100:
                    buckets['1-100'] += 1
                elif l <= 500:
                    buckets['101-500'] += 1
                elif l <= 1000:
                    buckets['501-1000'] += 1
                else:
                    buckets['1000+'] += 1
            length_data = pd.DataFrame({
                '长度区间': list(buckets.keys()),
                '数量': list(buckets.values())
            })
            st.bar_chart(length_data.set_index('长度区间'))
            # 下载长度分布数据
            st.download_button(
                "⬇️ 下载长度数据",
                data=length_data.to_csv(index=False).encode('utf-8-sig'),
                file_name="内容长度分布.csv",
                mime="text/csv",
                key="dl_length"
            )
        
        st.divider()
        
        # Row 3: Tree visualization with controls
        st.markdown("**🌳 知识树结构图**")
        
        # 添加控制选项
        ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns(4)
        with ctrl_col1:
            max_nodes = st.slider("显示节点数", min_value=10, max_value=min(100, len(atoms)), value=min(40, len(atoms)), step=10)
        with ctrl_col2:
            layout_dir = st.selectbox("布局方向", ["从上到下", "从左到右"], index=0)
        with ctrl_col3:
            show_level = st.multiselect("显示层级", options=[1, 2, 3, 4, 5], default=[1, 2, 3], format_func=lambda x: f"H{x}")
        with ctrl_col4:
            st.markdown("")  # 占位
            # 下载完整知识树 DOT 文件
            full_dot = self._generate_graphviz_enhanced(atoms, "TB")
            st.download_button(
                "⬇️ 下载完整图表 (DOT)",
                data=full_dot,
                file_name="知识树.dot",
                mime="text/plain",
                key="dl_dot"
            )
        
        try:
            # 根据选项过滤
            filtered_atoms = [a for a in atoms if a.level in show_level][:max_nodes]
            direction = "TB" if layout_dir == "从上到下" else "LR"
            dot_code = self._generate_graphviz_enhanced(filtered_atoms, direction)
            st.graphviz_chart(dot_code, use_container_width=True)
            st.caption(f"显示 {len(filtered_atoms)} / {len(atoms)} 个节点")
        except Exception as e:
            st.warning(f"图表渲染失败: {e}")
        
        st.divider()
        
        # Row 4: 来源文件分布（如果有多个文件）
        source_counts = {}
        for a in atoms:
            src = a.source_file
            source_counts[src] = source_counts.get(src, 0) + 1
        
        if len(source_counts) > 1:
            st.markdown("**📁 来源文件分布**")
            source_df = pd.DataFrame({
                '文件': list(source_counts.keys()),
                '原子数': list(source_counts.values())
            })
            st.bar_chart(source_df.set_index('文件'))
            st.download_button(
                "⬇️ 下载来源分布",
                data=source_df.to_csv(index=False).encode('utf-8-sig'),
                file_name="来源文件分布.csv",
                mime="text/csv",
                key="dl_source"
            )
            st.divider()
        
        # Row 5: Data table with more info and download
        st.markdown("**📋 完整数据表**")
        
        # 生成完整数据表
        full_df = pd.DataFrame([{
            'ID': a.id,
            '标题': a.title,
            '层级': a.level,
            '内容': a.content or "",
            '父节点': a.parent_title or "",
            '知识路径': a.path,
            '来源文件': a.source_file,
            '内容长度': len(a.content or ""),
            '子节点数': len([x for x in atoms if x.parent_id == a.id])
        } for a in atoms])
        
        # 显示预览（前100条）
        display_df = full_df.head(100).copy()
        display_df['标题'] = display_df['标题'].str[:40] + display_df['标题'].str[40:].apply(lambda x: '...' if x else '')
        display_df['内容'] = display_df['内容'].str[:50] + display_df['内容'].str[50:].apply(lambda x: '...' if x else '')
        st.dataframe(display_df[['标题', '层级', '内容长度', '子节点数', '知识路径', '来源文件']], use_container_width=True, height=400)
        
        if len(atoms) > 100:
            st.caption(f"预览前 100 条，共 {len(atoms)} 条")
        
        # 下载完整数据
        dl_col1, dl_col2, dl_col3 = st.columns(3)
        with dl_col1:
            st.download_button(
                "⬇️ 下载完整 CSV",
                data=full_df.to_csv(index=False).encode('utf-8-sig'),
                file_name="知识原子完整数据.csv",
                mime="text/csv",
                key="dl_full_csv"
            )
        with dl_col2:
            # JSON 格式
            json_data = json.dumps([{
                'id': a.id,
                'title': a.title,
                'level': a.level,
                'content': a.content or "",
                'parent_id': a.parent_id,
                'parent_title': a.parent_title,
                'path': a.path,
                'source_file': a.source_file
            } for a in atoms], ensure_ascii=False, indent=2)
            st.download_button(
                "⬇️ 下载 JSON",
                data=json_data,
                file_name="知识原子.json",
                mime="application/json",
                key="dl_json"
            )
        with dl_col3:
            # Markdown 格式
            md_content = self._generate_markdown_export(atoms)
            st.download_button(
                "⬇️ 下载 Markdown",
                data=md_content.encode('utf-8'),
                file_name="知识原子.md",
                mime="text/markdown",
                key="dl_md"
            )
    
    def _generate_markdown_export(self, atoms: List[KnowledgeAtom]) -> str:
        """生成 Markdown 格式的知识原子导出"""
        lines = ["# 知识原子导出\n"]
        lines.append(f"> 共 {len(atoms)} 个知识原子\n")
        lines.append("---\n")
        
        # 按层级组织
        root_atoms = [a for a in atoms if a.parent_id is None]
        
        def render_atom(atom: KnowledgeAtom, depth: int = 0):
            prefix = "#" * (depth + 2)  # Start from ##
            lines.append(f"{prefix} {atom.title}\n")
            lines.append(f"**路径**: `{atom.path}`\n")
            if atom.content:
                lines.append(f"\n{atom.content}\n")
            lines.append("")
            
            # Render children
            children = [a for a in atoms if a.parent_id == atom.id]
            for child in children:
                render_atom(child, depth + 1)
        
        for root in root_atoms:
            render_atom(root)
        
        return '\n'.join(lines)
    
    def _generate_graphviz_enhanced(self, atoms: List[KnowledgeAtom], direction: str = "TB") -> str:
        """生成增强版 Graphviz DOT 格式图表"""
        lines = [
            'digraph G {',
            f'    rankdir={direction};',
            '    bgcolor="transparent";',
            '    node [shape=box, style="rounded,filled", fontname="Microsoft YaHei,Arial", fontsize=10];',
            '    edge [color="#888888", arrowsize=0.7];',
            '    graph [ranksep=0.5, nodesep=0.3];'
        ]
        
        # Color mapping for levels with gradients
        colors = {
            1: '#ff6b6b',  # Red
            2: '#ffa94d',  # Orange
            3: '#ffd43b',  # Yellow
            4: '#69db7c',  # Green
            5: '#74c0fc'   # Blue
        }
        
        # Build parent set for edge validation
        atom_ids = {a.id for a in atoms}
        
        for atom in atoms:
            safe_title = atom.title[:20].replace('"', "'").replace('\n', ' ').replace('\\', '/')
            if len(atom.title) > 20:
                safe_title += '...'
            node_id = 'n' + atom.id[:8].replace('-', '')
            color = colors.get(atom.level, '#e9ecef')
            
            # Add node with tooltip
            tooltip = f"{atom.title}\\n层级: H{atom.level}\\n内容: {len(atom.content or '')} 字"
            lines.append(f'    {node_id} [label="{safe_title}", fillcolor="{color}", tooltip="{tooltip}"];')
            
            # Add edge only if parent is in the filtered set
            if atom.parent_id and atom.parent_id in atom_ids:
                parent_id = 'n' + atom.parent_id[:8].replace('-', '')
                lines.append(f'    {parent_id} -> {node_id};')
        
        # Add legend
        lines.append('    subgraph cluster_legend {')
        lines.append('        label="图例";')
        lines.append('        style=dashed;')
        lines.append('        fontsize=9;')
        lines.append('        legend1 [label="H1 章节", fillcolor="#ff6b6b"];')
        lines.append('        legend2 [label="H2 小节", fillcolor="#ffa94d"];')
        lines.append('        legend3 [label="H3 主题", fillcolor="#ffd43b"];')
        lines.append('        legend1 -> legend2 -> legend3 [style=invis];')
        lines.append('    }')
        
        lines.append('}')
        return '\n'.join(lines)
    
    def _render_export_section(self, atoms: List[KnowledgeAtom]):
        """渲染导出选项 - 优化版本，按需生成"""
        st.subheader("📥 导出知识原子")
        st.caption(f"来源文件: {st.session_state.source_file} | 共 {len(atoms)} 个知识原子")
        
        # Three columns for export buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 📄 CSV")
            st.caption("Excel 兼容格式")
            
            # 按需生成 CSV
            if st.button("生成 CSV", key="gen_csv", use_container_width=True):
                with st.spinner("生成中..."):
                    self._generate_csv(atoms)
            
            if st.session_state.csv_data:
                st.download_button(
                    label="⬇️ 下载 CSV",
                    data=st.session_state.csv_data,
                    file_name=f"{st.session_state.source_file or 'export'}_atoms.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with col2:
            st.markdown("### 📚 Obsidian")
            st.caption("知识库 ZIP 包")
            
            # 按需生成 ZIP
            if st.button("生成 ZIP", key="gen_zip", use_container_width=True):
                with st.spinner("生成中..."):
                    self._generate_zip(atoms)
            
            if st.session_state.zip_data:
                st.download_button(
                    label="⬇️ 下载 ZIP",
                    data=st.session_state.zip_data,
                    file_name=f"{st.session_state.source_file or 'export'}_obsidian.zip",
                    mime="application/zip",
                    use_container_width=True
                )
        
        with col3:
            st.markdown("### 🐦 飞书")
            st.caption("同步到多维表格")
            if st.session_state.get('lark_configured'):
                if st.button("🚀 同步到飞书", key="lark_sync_btn", use_container_width=True, type="primary"):
                    self._export_lark(
                        atoms,
                        st.session_state.lark_app_id,
                        st.session_state.lark_app_secret,
                        st.session_state.lark_app_token,
                        st.session_state.lark_table_id
                    )
            else:
                st.info("请先配置飞书 API ↓")
        
        st.divider()
        
        # Lark config in expander
        with st.expander("⚙️ 飞书 API 配置", expanded=not st.session_state.get('lark_configured')):
            col1, col2 = st.columns(2)
            with col1:
                app_id = st.text_input("App ID", placeholder="cli_xxxxxxxxxx", key="lark_app_id_input")
                app_token = st.text_input("App Token", placeholder="bascnxxxxxxxxxx", key="lark_app_token_input")
            with col2:
                app_secret = st.text_input("App Secret", type="password", placeholder="xxxxxxxxxx", key="lark_app_secret_input")
                table_id = st.text_input("Table ID", placeholder="tblxxxxxxxxxx", key="lark_table_id_input")
            
            st.caption("� 飞书多维配表格需要的字段：原子ID、标题、内容、层级、父节点、来源文件、知识路径")
            
            if st.button("💾 保存配置", use_container_width=True):
                if all([app_id, app_secret, app_token, table_id]):
                    st.session_state.lark_app_id = app_id
                    st.session_state.lark_app_secret = app_secret
                    st.session_state.lark_app_token = app_token
                    st.session_state.lark_table_id = table_id
                    st.session_state.lark_configured = True
                    st.success("✅ 配置已保存")
                    st.rerun()
                else:
                    st.error("请填写所有配置项")
    
    def _generate_csv(self, atoms: List[KnowledgeAtom]):
        """生成 CSV 数据"""
        try:
            exporter = CSVExporter()
            result = exporter.export(atoms)
            if result.success and result.file_path:
                with open(result.file_path, 'rb') as f:
                    st.session_state.csv_data = f.read()
                os.unlink(result.file_path)
                st.success("CSV 生成完成！")
        except Exception as e:
            st.error(f"生成失败: {e}")
    
    def _generate_zip(self, atoms: List[KnowledgeAtom]):
        """生成 Obsidian ZIP 数据"""
        try:
            exporter = ObsidianExporter()
            result = exporter.export(atoms)
            if result.success and result.file_path:
                with open(result.file_path, 'rb') as f:
                    st.session_state.zip_data = f.read()
                os.unlink(result.file_path)
                st.success("ZIP 生成完成！")
        except Exception as e:
            st.error(f"生成失败: {e}")
    
    def _export_lark(self, atoms: List[KnowledgeAtom], app_id: str, app_secret: str, app_token: str, table_id: str):
        """导出到飞书"""
        try:
            with st.spinner("正在同步到飞书..."):
                exporter = LarkExporter(app_id, app_secret, app_token, table_id)
                result = exporter.export(atoms)
                
                if result.success:
                    st.success(result.message)
                else:
                    st.error(result.message)
        except Exception as e:
            st.error(f"同步失败: {str(e)}")


def main():
    """Main entry point."""
    app = KnowledgeAtomizerApp()
    app.run()


if __name__ == "__main__":
    main()
