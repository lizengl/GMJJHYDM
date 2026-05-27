"""

国民经济行业分类智能助手

基于 RAG 技术，根据企业描述自动识别行业类别与代码。
"""
import streamlit as st
from rag import RagService, is_followup
import config_data as config

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(
    page_title="行业分类助手",
    page_icon="🏭",
    layout="centered",
)

# ── 自定义样式 ────────────────────────────────────────────
st.markdown("""
<style>
    /* 全局 */
    .stApp { background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%); }
    .main .block-container { padding-top: 1.5rem; max-width: 860px; }

    /* 标题 */
    .hero { text-align: center; padding: 2rem 0 1rem; }
    .hero h1 { font-size: 2rem; font-weight: 700; color: #1e293b; margin: 0; }
    .hero p { color: #64748b; font-size: 0.95rem; margin-top: 0.3rem; }

    /* 聊天消息 */
    .stChatMessage { border-radius: 12px !important; padding: 0.75rem 1rem !important; margin: 0.5rem 0 !important; }
    [data-testid="stChatMessage"][aria-label*="user"] { background: #3b82f6 !important; }
    [data-testid="stChatMessage"][aria-label*="user"] p { color: #fff !important; }
    [data-testid="stChatMessage"][aria-label*="assistant"] { background: #ffffff !important; border: 1px solid #e2e8f0 !important; }
    [data-testid="stChatMessage"][aria-label*="assistant"] p { color: #334155 !important; }

    /* 聊天气泡箭头 */
    [data-testid="stChatMessage"]::before { display: none; }

    /* 输入框 */
    [data-testid="stChatInput"] textarea {
        border-radius: 12px !important; border: 1.5px solid #cbd5e1 !important;
        background: #fff !important; padding: 0.75rem 1rem !important;
    }
    [data-testid="stChatInput"] textarea:focus { border-color: #3b82f6 !important; box-shadow: 0 0 0 2px rgba(59,130,246,0.15) !important; }

    /* 侧边栏 */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%) !important; }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #f8fafc !important; }
    [data-testid="stSidebar"] hr { border-color: #334155 !important; }

    /* 状态标签 */
    .status-badge {
        display: inline-block; padding: 0.2rem 0.6rem; border-radius: 20px;
        font-size: 0.8rem; font-weight: 500; margin: 0.3rem 0;
    }
    .status-ok { background: #16653430; color: #15803d; }
    .status-info { background: #1e3a5f30; color: #2563eb; }

    /* Loading */
    .stSpinner > div { border-top-color: #3b82f6 !important; }
</style>
""", unsafe_allow_html=True)

# ── 侧边栏 ────────────────────────────────────────────────
with st.sidebar:
    st.title("🏭 行业分类助手")
    st.caption("国民经济行业分类 · 智能识别")
    st.divider()

    st.markdown("### 当前状态")
    st.markdown(f'<span class="status-badge status-ok">模型：{config.chat_model_name}</span>', unsafe_allow_html=True)
    st.markdown(f'<span class="status-badge status-info">检索结果数：{config.top_k}</span>', unsafe_allow_html=True)

    st.divider()
    st.markdown("### 使用说明")
    st.caption("描述你企业的经营活动，AI 会自动匹配最合适的国民经济行业类别并返回行业代码。")
    st.caption("例如：「我们公司主要做新能源汽车动力电池的研发、生产和销售」")

    st.divider()
    with st.expander("历史会话", expanded=False):
        if st.button("清除对话记录"):
            st.session_state["message"] = [{"role": "assistant", "content": "你好，我是国民经济行业分类助手。请描述你企业的经营活动，我会帮你匹配合适的行业类别和代码。"}]
            st.session_state.pop("last_company_desc", None)
            st.rerun()

# ── 主界面 ────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>国民经济行业分类助手</h1>
    <p>描述你的企业经营活动，智能匹配行业类别与代码</p>
</div>
""", unsafe_allow_html=True)

# 初始化
if "message" not in st.session_state:
    st.session_state["message"] = [
        {"role": "assistant", "content": "你好，我是国民经济行业分类助手。\n\n请描述你企业的经营活动，我会帮你匹配最合适的**行业类别**和**行业代码**。\n\n例如：「我们公司主要做新能源汽车动力电池的研发、生产和销售」"}
    ]

if "rag" not in st.session_state:
    st.session_state["rag"] = RagService()

if "last_company_desc" not in st.session_state:
    st.session_state["last_company_desc"] = None

# 渲染历史消息
for message in st.session_state["message"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 用户输入
prompt = st.chat_input("请描述你企业的经营活动...")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state["message"].append({"role": "user", "content": prompt})

    # 构建检索参数：追问时用历史中的企业描述做检索词
    chain_input = {"input": prompt}
    is_follow = is_followup(prompt) and st.session_state["last_company_desc"] is not None
    if is_follow:
        chain_input["retrieval_query"] = st.session_state["last_company_desc"]

    ai_res_list = []
    with st.chat_message("assistant"):
        with st.spinner("AI 分析中..."):
            res_stream = st.session_state["rag"].chain.stream(
                chain_input, config.session_config
            )

            def capture(generator, cache_list):
                for chunk in generator:
                    cache_list.append(chunk)
                    yield chunk

            st.write_stream(capture(res_stream, ai_res_list))

    st.session_state["message"].append({"role": "assistant", "content": "".join(ai_res_list)})

    # 非追问时，把当前输入当作新的企业描述记录下来
    if not is_follow:
        st.session_state["last_company_desc"] = prompt