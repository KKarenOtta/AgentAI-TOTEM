def rank(items: list[dict]) -> list[dict]:
    return sorted(
        items,
        key=lambda x: (x.get("score", 0) + x.get("uses", 0)),
        reverse=True
    )
