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
        """渲染树形视图"""
        st.subheader("🌳 知识树结构")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**层级结构**")
            root_atoms = [a for a in atoms if a.parent_id is None]
            
            def render_tree_node(atom: KnowledgeAtom, depth: int = 0):
                indent = "　　" * depth
                prefix = "├─ " if depth > 0 else ""
                level_colors = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🔵"}
                level_icon = level_colors.get(atom.level, "⚪")
                
                if st.button(
                    f"{indent}{prefix}{level_icon} {atom.title}",
                    key=f"tree_{atom.id}",
                    use_container_width=True
                ):
                    st.session_state.selected_atom = atom
                
                children = [a for a in atoms if a.parent_id == atom.id]
                for child in children:
                    render_tree_node(child, depth + 1)
            
            for root in root_atoms:
                render_tree_node(root)
        
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
                st.info("👈 点击左侧节点查看详情")
    
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
        """渲染可视化图表"""
        import pandas as pd
        
        st.subheader("📊 知识结构可视化")
        
        stats = compute_statistics(atoms)
        
        # Row 1: Key metrics
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
        
        # Row 2: Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📊 层级分布**")
            level_data = pd.DataFrame({
                '层级': [f'H{i}' for i in range(1, 6)],
                '数量': [stats.level_counts.get(i, 0) for i in range(1, 6)]
            })
            st.bar_chart(level_data.set_index('层级'))
        
        with col2:
            st.markdown("**📏 内容长度分布**")
            # Group content lengths into buckets
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
        
        st.divider()
        
        # Row 3: Tree visualization using graphviz
        st.markdown("**🌳 知识树结构图**")
        
        try:
            # Generate graphviz DOT format
            dot_code = self._generate_graphviz(atoms)
            st.graphviz_chart(dot_code)
        except Exception as e:
            st.warning(f"图表渲染失败: {e}")
            st.code(self._generate_mermaid(atoms), language="mermaid")
        
        st.divider()
        
        # Row 4: Data table
        st.markdown("**📋 数据概览**")
        df = pd.DataFrame([{
            '标题': a.title[:30] + ('...' if len(a.title) > 30 else ''),
            '层级': f'H{a.level}',
            '内容长度': len(a.content or ""),
            '子节点数': len([x for x in atoms if x.parent_id == a.id]),
            '路径深度': a.path.count(">") + 1
        } for a in atoms[:50]])
        st.dataframe(df, use_container_width=True)
        
        if len(atoms) > 50:
            st.caption(f"仅显示前 50 条，共 {len(atoms)} 条")
    
    def _generate_graphviz(self, atoms: List[KnowledgeAtom]) -> str:
        """生成 Graphviz DOT 格式图表"""
        lines = [
            'digraph G {',
            '    rankdir=TB;',
            '    node [shape=box, style="rounded,filled", fontname="Arial"];',
            '    edge [color="#666666"];'
        ]
        
        # Color mapping for levels
        colors = {1: '#ff6b6b', 2: '#ffa94d', 3: '#ffd43b', 4: '#69db7c', 5: '#74c0fc'}
        
        # Limit nodes for readability
        display_atoms = atoms[:40]
        
        for atom in display_atoms:
            safe_title = atom.title[:15].replace('"', "'").replace('\n', ' ')
            if len(atom.title) > 15:
                safe_title += '...'
            node_id = 'n' + atom.id[:8].replace('-', '')
            color = colors.get(atom.level, '#e9ecef')
            lines.append(f'    {node_id} [label="{safe_title}", fillcolor="{color}"];')
            
            if atom.parent_id:
                parent_id = 'n' + atom.parent_id[:8].replace('-', '')
                lines.append(f'    {parent_id} -> {node_id};')
        
        if len(atoms) > 40:
            lines.append(f'    more [label="... 还有 {len(atoms) - 40} 个节点", style="dashed"];')
        
        lines.append('}')
        return '\n'.join(lines)
    
    def _generate_mermaid(self, atoms: List[KnowledgeAtom]) -> str:
        """生成 Mermaid 图表代码"""
        lines = ["graph TD"]
        
        # Limit to first 30 nodes for readability
        display_atoms = atoms[:30]
        
        for atom in display_atoms:
            safe_title = atom.title[:20].replace('"', "'").replace("[", "(").replace("]", ")")
            node_id = atom.id[:8]
            lines.append(f'    {node_id}["{safe_title}"]')
            
            if atom.parent_id:
                parent_id = atom.parent_id[:8]
                lines.append(f'    {parent_id} --> {node_id}')
        
        if len(atoms) > 30:
            lines.append(f'    more["... 还有 {len(atoms) - 30} 个节点"]')
        
        return "\n".join(lines)
    
    def _render_export_section(self, atoms: List[KnowledgeAtom]):
        """渲染导出选项"""
        st.subheader("📥 导出知识原子")
        st.caption(f"来源文件: {st.session_state.source_file} | 共 {len(atoms)} 个知识原子")
        
        # Initialize session state for exports
        if 'csv_data' not in st.session_state:
            st.session_state.csv_data = None
        if 'zip_data' not in st.session_state:
            st.session_state.zip_data = None
        
        # Pre-generate exports
        self._prepare_exports(atoms)
        
        # Three columns for export buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 📄 CSV")
            st.caption("Excel 兼容格式")
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
            # Show sync button only if config exists
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
            
            st.caption("💡 飞书多维表格需要的字段：原子ID、标题、内容、层级、父节点、来源文件、知识路径")
            
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
    
    def _prepare_exports(self, atoms: List[KnowledgeAtom]):
        """预生成导出文件"""
        # Generate CSV if not exists
        if st.session_state.csv_data is None:
            try:
                exporter = CSVExporter()
                result = exporter.export(atoms)
                if result.success and result.file_path:
                    with open(result.file_path, 'rb') as f:
                        st.session_state.csv_data = f.read()
                    os.unlink(result.file_path)
            except Exception:
                pass
        
        # Generate ZIP if not exists
        if st.session_state.zip_data is None:
            try:
                exporter = ObsidianExporter()
                result = exporter.export(atoms)
                if result.success and result.file_path:
                    with open(result.file_path, 'rb') as f:
                        st.session_state.zip_data = f.read()
                    os.unlink(result.file_path)
            except Exception:
                pass
    
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
