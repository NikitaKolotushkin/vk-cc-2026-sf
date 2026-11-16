from pathlib import Path


def write(folder: Path, status: str, summary: str, lines: list[str]) -> None:
    body = [f"status: {status}", "", summary, ""]
    body.extend(lines)
    (folder / "verdict.txt").write_text("\n".join(body) + "\n", encoding="utf-8")
    print(f"{folder.name}: {status}")
    print(summary)


def pp_call(diff: float, confirm_at: float = 5, reject_below: float = 2) -> str:
    if diff >= confirm_at:
        return "подтверждена"
    if diff < reject_below:
        return "отвергнута"
    return "промежуточная"
