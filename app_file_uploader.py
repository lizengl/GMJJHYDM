"""
基于Streamlit完成web网页上传服务

Streamlit：当WEB页面元素发生变化，则代码重新执行一遍
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

#添加网页标题
st.title("知识库更新服务")

#file_uploader
uploader_file = st.file_uploader(
    "请上传TXT或Excel文件",
    type=['txt', 'xlsx'],
    accept_multiple_files=False,
)

# session_state就是一个字典
if "service" not in st.session_state:
    st.session_state["service"] = KnowledgeBaseService()

if uploader_file is not None:
    file_name = uploader_file.name
    file_type = uploader_file.type
    file_size = uploader_file.size / 1024

    st.subheader(f"文件名：{file_name}")
    st.subheader(f"格式：{file_type} | 大小：{file_size:.2f} KB")

    # 根据文件类型读取内容
    if file_name.endswith('.xlsx'):
        text = excel_to_text(uploader_file.getvalue())
    else:
        text = uploader_file.getvalue().decode("utf-8")

    with st.spinner("载入知识库中。。。"):
        time.sleep(1)
        result = st.session_state["service"].upload_by_str(text, file_name)
        st.write(result)