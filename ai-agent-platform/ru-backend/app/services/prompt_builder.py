from app import models


def build_system_prompt(agent: models.Agent, knowledge_context: str = "") -> str:
    parts = [
        f"Ты — {agent.name}, {agent.role}.",
        f"Твой характер и стиль общения: {agent.personality}.",
        f"Твоя основная задача: {agent.goal}.",
    ]

    if agent.restrictions:
        parts.append(f"Ограничения, которые ты обязан соблюдать: {agent.restrictions}.")

    if knowledge_context:
        parts.append(
            "Используй следующую информацию из базы знаний, если она relevant "
            "к вопросу пользователя, и не выдумывай факты, которых там нет:\n"
            f"{knowledge_context}"
        )

    parts.append("Отвечай на русском языке, если пользователь не попросит иное.")

    return "\n".join(parts)
