conversation = [{"role": "system", "content": "You are a professional assistant, coding expert, and MLOps subject matter expert."}]

def ensure_alternating_roles():
    global conversation
    filtered = [conversation[0]]
    for i in range(1, len(conversation)):
        if conversation[i]["role"] != conversation[i - 1]["role"]:
            filtered.append(conversation[i])
    conversation[:] = filtered

def reset_conversation():
    global conversation
    conversation = [{"role": "system", "content": "You are a professional assistant and coding expert."}]