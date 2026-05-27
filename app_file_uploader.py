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

st.set_page_config(page_title="知识库更新", page_icon="📚")
st.title("知识库更新服务")

# 初始化服务
if "service" not in st.session_state:
    st.session_state["service"] = KnowledgeBaseService()

# 文件上传
uploader_file = st.file_uploader(
    "请上传 TXT 或 Excel 文件",
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
    with st.expander("内容预览", expanded=False):
        st.text(preview_text[:500] + ("..." if len(preview_text) > 500 else ""))

    # 确认上传按钮
    if not st.session_state.get("upload_done", False):
        if st.button("确认上传", type="primary"):
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
        if st.button("上传另一个文件"):
            st.session_state["pending_text"] = None
            st.session_state["pending_filename"] = None
            st.session_state["upload_done"] = False
            st.rerun()