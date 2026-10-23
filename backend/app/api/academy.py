from __future__ import annotations

from flask import Blueprint, jsonify

from ..a11y.wcag import CATALOG
from ..data import academy as content
from ..repositories import academy as repo
from ..schemas.requests import QuizIn
from .support import ApiError, body, db, lang, not_found

bp = Blueprint("academy", __name__)


def _texts(lesson: dict, current: str) -> dict:
    return lesson.get(current) or lesson["en"]


def _summary(lesson: dict, current: str, progress: dict) -> dict:
    t = _texts(lesson, current)
    p = progress.get(lesson["id"])
    return {
        "id": lesson["id"], "title": t["title"], "summary": t["summary"], "minutes": lesson["minutes"],
        "questions": len(lesson["quiz"]), "wcag": [CATALOG[s].as_dict() for s in lesson["wcag"] if s in CATALOG],
        "progress": {"attempts": p["attempts"], "best_score": p["best_score"], "total": p["total"], "completed": bool(p["completed_at"])} if p else None,
    }


@bp.get("/academy")
def list_lessons():
    current, progress = lang(), repo.all_progress(db())
    items = [_summary(lesson, current, progress) for lesson in content.LESSONS]
    return jsonify(items=items, completed=sum(1 for i in items if i["progress"] and i["progress"]["completed"]), total=len(items))


@bp.get("/academy/<lesson_id>")
def get_lesson(lesson_id: str):
    lesson = content.BY_ID.get(lesson_id)
    if lesson is None:
        raise not_found("Урок")
    current = lang()
    t = _texts(lesson, current)
    quiz = [{"id": i, "question": _texts(q, current)["q"], "options": _texts(q, current)["options"]} for i, q in enumerate(lesson["quiz"])]
    order = [l["id"] for l in content.LESSONS]
    idx = order.index(lesson_id)
    return jsonify({**_summary(lesson, current, repo.all_progress(db())), "sections": t["sections"], "example": t.get("example"), "quiz": quiz,
                    "next": order[idx + 1] if idx + 1 < len(order) else None, "prev": order[idx - 1] if idx > 0 else None})


@bp.post("/academy/<lesson_id>/quiz")
def submit_quiz(lesson_id: str):
    lesson = content.BY_ID.get(lesson_id)
    if lesson is None:
        raise not_found("Урок")
    data = body(QuizIn)
    quiz = lesson["quiz"]
    if len(data.answers) != len(quiz):
        raise ApiError(422, "validation_error", "Нужно ответить на все вопросы")
    current = lang()
    results, score = [], 0
    for i, (q, chosen) in enumerate(zip(quiz, data.answers)):
        t = _texts(q, current)
        if not 0 <= chosen < len(t["options"]):
            raise ApiError(422, "validation_error", "Недопустимый вариант ответа")
        ok = chosen == q["answer"]
        score += ok
        results.append({"id": i, "correct": ok, "chosen": chosen, "answer": q["answer"], "explain": t["explain"]})
    passed = score / len(quiz) >= content.PASS_RATIO
    progress = repo.record(db(), lesson_id, score, len(quiz), passed)
    return jsonify(score=score, total=len(quiz), passed=passed, results=results,
                   progress={"attempts": progress["attempts"], "best_score": progress["best_score"], "completed": bool(progress["completed_at"])})
