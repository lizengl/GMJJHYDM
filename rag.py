import os
import sys
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableWithMessageHistory, RunnableLambda
from file_history_store import get_history
from vector_stores import VectorStoreService
from langchain_community.embeddings import DashScopeEmbeddings
import config_data as config
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_models.tongyi import ChatTongyi


def _check_api_key():
    if "DASHSCOPE_API_KEY" not in os.environ:
        sys.exit(
            "\n 未检测到 DASHSCOPE_API_KEY 环境变量。\n"
            " 本地运行: export DASHSCOPE_API_KEY='your-key'\n"
            " Streamlit Cloud: 在 Settings -> Secrets 中添加:\n"
            '   DASHSCOPE_API_KEY = "your-key"\n'
        )


_FOLLOWUP_KEYWORDS = {
    "我们公司", "我们企业", "刚才", "之前", "前面", "代码", "再来", "确认",
    "是什么", "查一下", "帮我看看", "你刚才", "你说", "那个", "哪个",
}

def _is_followup(input_text: str) -> bool:
    text = input_text.strip()
    if len(text) <= 15 and any(kw in text for kw in _FOLLOWUP_KEYWORDS):
        return True
    if text.startswith(("我们", "刚才", "之前", "那个", "你")):
        return True
    return False


SYSTEM_PROMPT = """你是国民经济行业分类专家。

回答要求：
- 直接输出最终答案，严禁输出思考过程、推理过程、自我对话。
- 回答简洁，不超过100字。
- 严格按照指定格式输出，不要添加额外解释。

核心任务：根据用户的企业描述，匹配最合适的行业类别并给出代码。

追问处理规则（非常重要）：
- 如果用户的问题是追问（如"我们公司代码是多少"、"刚才那个行业"），说明用户之前已经描述过企业，请直接从对话历史中查找之前给你的结论和代码，直接复述即可，不要重新匹配。
- 只有在用户首次描述企业或提供新的企业信息时，才需要重新匹配行业。

匹配规则：
1. 优先匹配主营业务，忽略次要或附带业务
2. 如果参考资料中有多个候选，选择描述最接近的一个
3. 如果参考资料中没有明显匹配的行业，选择最接近的并说明不确定性

参考资料:{context}"""

FORMAT_PROMPT = """请严格按以下格式回答（三行，不要多也不要少）：
行业代码：<代码>
行业名称：<名称>
判断依据：<一句话简要说明>"""


class RagService(object):
    def __init__(self):
        _check_api_key()

        self.vector_service = VectorStoreService(
            embedding=DashScopeEmbeddings(model=config.embedding_model_name)
        )

        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("system", FORMAT_PROMPT),
                ("system", "对话历史："),
                MessagesPlaceholder("history"),
                ("user", "{input}")
            ]
        )

        self.chat_model = ChatTongyi(
            model=config.chat_model_name,
            model_kwargs={"enable_thinking": False},
        )

        self.chain = self.__get_chain()

    def __get_chain(self):
        retriever = self.vector_service.get_retriever()

        def format_document(docs: list[Document]):
            if not docs:
                return "无相关参考资料"
            formatted_str = ""
            for doc in docs:
                formatted_str += f"文档片段：{doc.page_content}\n文档元数据：{doc.metadata}\n\n"
            return formatted_str

        def format_for_retriever(value: dict) -> str:
            input_text = value["input"]
            if _is_followup(input_text):
                return f"用户追问：{input_text}"
            return input_text

        def format_for_prompt_template(value):
            new_value = {}
            new_value["input"] = value["input"]["input"]
            new_value["context"] = value["context"]
            new_value["history"] = value["input"]["history"]
            return new_value

        chain = (
            {
                "input": RunnablePassthrough(),
                "context": RunnableLambda(format_for_retriever) | retriever | format_document
            } | RunnableLambda(format_for_prompt_template) | self.prompt_template | self.chat_model | StrOutputParser()
        )

        conversation_chain = RunnableWithMessageHistory(
            chain,
            get_history,
            input_messages_key="input",
            history_messages_key="history",
        )

        return conversation_chain