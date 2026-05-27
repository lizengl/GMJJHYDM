"""
知识库上传服务

支持 TXT 和 Excel 文件上传至向量数据库。
"""
import io
import time
import streamlit as st
import pandas as pd
from knowledge_base import KnowledgeBaseService

def excel_to_text(file_bytes):
    """将Excel文件的所有sheet转换为文本字符串"""
    sheets = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
    parts = []
    for sheet_name, df in sheets.items():
        parts.append(f"【{sheet_name}】")
        parts.append(df.to_string(index=False))
    return "\n".join(parts)

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(page_title="知识库管理", page_icon="📚", layout="centered")

# ── 自定义样式 ────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%); }
    .main .block-container { padding-top: 1.5rem; max-width: 800px; }

    /* 上传区域 */
    [data-testid="stFileUploader"] section {
        border: 2px dashed #94a3b8 !important; border-radius: 16px !important;
        padding: 2rem !important; background: #fff !important;
        transition: border-color 0.2s !important;
    }
    [data-testid="stFileUploader"]:hover section { border-color: #3b82f6 !important; }

    /* 按钮 */
    .stButton > button {
        border-radius: 10px !important; font-weight: 600 !important;
        padding: 0.6rem 2rem !important; transition: all 0.2s !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(37,99,235,0.35) !important; }

    /* 指标卡片 */
    [data-testid="stMetric"] {
        background: #fff !important; border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important; padding: 1rem !important;
    }
    [data-testid="stMetric"] label { color: #64748b !important; font-size: 0.8rem !important; }
    [data-testid="stMetric"] [data-testid="stMetricValue"] { color: #1e293b !important; }

    /* 展开/预览 */
    .stExpander { border-radius: 12px !important; border: 1px solid #e2e8f0 !important; background: #fff !important; }
    .stExpander > div:first-child { font-weight: 600 !important; color: #475569 !important; }

    /* 预览文本框 */
    .stExpander .stText { background: #f8fafc !important; border-radius: 8px !important; padding: 1rem !important; font-family: "SF Mono", "Cascadia Code", monospace !important; font-size: 0.85rem !important; }

    /* 成功/提示 */
    .stSuccess { border-radius: 10px !important; }

    /* 侧边栏 */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%) !important; }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #f8fafc !important; }
    [data-testid="stSidebar"] hr { border-color: #334155 !important; }
</style>
""", unsafe_allow_html=True)

# ── 侧边栏 ────────────────────────────────────────────────
with st.sidebar:
    st.title("📚 知识库管理")
    st.caption("上传知识文件至向量数据库")
    st.divider()
    st.markdown("### 支持格式")
    st.caption("- TXT 纯文本文件")
    st.caption("- Excel 表格 (.xlsx)")
    st.divider()
    st.markdown("### 说明")
    st.caption("文件上传后将自动分割并存入向量数据库，供行业分类助手检索使用。重复文件会自动跳过。")

# ── 主界面 ────────────────────────────────────────────────
st.title("知识库更新服务")
st.caption("上传 TXT 或 Excel 文件，内容将自动向量化并存入知识库")

st.divider()

# 初始化服务
if "service" not in st.session_state:
    st.session_state["service"] = KnowledgeBaseService()

# 文件上传
uploader_file = st.file_uploader(
    "拖拽文件到此处或点击选择",
    type=["txt", "xlsx"],
    accept_multiple_files=False,
)

if uploader_file is not None:
    file_name = uploader_file.name
    file_type = uploader_file.type
    file_size = uploader_file.size / 1024

    st.divider()

    col1, col2, col3 = st.columns(3)
    col1.metric("文件名", file_name)
    col2.metric("格式", file_type or "未知")
    col3.metric("大小", f"{file_size:.1f} KB")

    # 解析文件内容
    if "pending_text" not in st.session_state or st.session_state.get("pending_filename") != file_name:
        if file_name.endswith(".xlsx"):
            text = excel_to_text(uploader_file.getvalue())
        else:
            text = uploader_file.getvalue().decode("utf-8")
        st.session_state["pending_text"] = text
        st.session_state["pending_filename"] = file_name
        st.session_state["upload_done"] = False

    # 显示内容预览（前500字）
    preview_text = st.session_state["pending_text"]
    with st.expander(f"内容预览（共 {len(preview_text):,} 字符）", expanded=False):
        st.text(preview_text[:500] + ("..." if len(preview_text) > 500 else ""))

    # 确认上传按钮
    if not st.session_state.get("upload_done", False):
        st.divider()
        if st.button("确认上传到知识库", type="primary", use_container_width=True):
            with st.spinner("正在载入知识库..."):
                time.sleep(0.5)
                result = st.session_state["service"].upload_by_str(
                    st.session_state["pending_text"], file_name
                )
                st.session_state["upload_done"] = True
                st.session_state["upload_result"] = result
                st.rerun()
    else:
        st.success(st.session_state.get("upload_result", "上传完成"))
        if st.button("上传另一个文件", use_container_width=True):
            st.session_state["pending_text"] = None
            st.session_state["pending_filename"] = None
            st.session_state["upload_done"] = False
            st.rerun()