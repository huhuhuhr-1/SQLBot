from apps.ai_model.model_factory import get_default_config, LLMFactory


class BaseChatModel:
    pass


class LLMManager:
    @staticmethod
    def get_default_llm_sync() -> BaseChatModel:
        """
        同步方式获取默认配置的LLM实例

        Returns:
            BaseChatModel: LLM实例
        """
        # 如果有同步的配置获取方式
        # config = get_default_config_sync()
        # llm_instance = LLMFactory.create_llm(config)
        # return llm_instance.llm
        pass

    @staticmethod
    async def get_default_llm() -> BaseChatModel:
        """
        异步方式获取默认配置的LLM实例

        Returns:
            BaseChatModel: LLM实例
        """
        config = await get_default_config()
        llm_instance = LLMFactory.create_llm(config)
        return llm_instance.llm
