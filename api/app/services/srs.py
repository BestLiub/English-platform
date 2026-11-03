"""记忆调度（FSRS 封装）。

两个设计考虑：

1. py-fsrs 的 API 在 v3 / v4 / v5 之间改过，所以这里做兼容探测。导入失败或
   调用形态不匹配时，自动退回到内置的简易调度器。应用永远能跑起来，
   不会因为一个第三方包的 API 变动整站打不开。
2. 上层（routers）只依赖 CardState / review() 这一组接口。
   将来换算法、换参数，只改这个文件。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

RATING_NAMES = {1: "Again", 2: "Hard", 3: "Good", 4: "Easy"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class CardState:
    stability: float = 0.0
    difficulty: float = 0.0
    state: int = 0          # 0 新 1 学习中 2 复习 3 重学
    step: int = 0
    interval_days: float = 0.0
    reps: int = 0
    lapses: int = 0
    due: datetime | None = None
    last_review: datetime | None = None


@dataclass
class ScheduleResult:
    state: CardState
    interval_days: float = 0.0
    source: str = field(default="fsrs")   # fsrs / fallback


# ---------------------------------------------------------------- py-fsrs

try:  # pragma: no cover - 取决于环境里装了什么版本
    from fsrs import Card, Rating, Scheduler, State  # type: ignore

    _scheduler = Scheduler()
    _HAS_FSRS = True
except Exception:  # noqa: BLE001
    _HAS_FSRS = False
    logger.info("py-fsrs 不可用，使用内置简易调度器")


# 数据库里 0=新 1=学习中 2=复习 3=重学；
# fsrs 只有 Learning(1) / Review(2) / Relearning(3)，新卡就是 Learning + stability=None
if _HAS_FSRS:
    _DB_TO_FSRS = {0: State.Learning, 1: State.Learning, 2: State.Review, 3: State.Relearning}
    _FSRS_TO_DB = {State.Learning: 1, State.Review: 2, State.Relearning: 3}
else:
    _DB_TO_FSRS = {}
    _FSRS_TO_DB = {}


def _to_aware(dt: datetime | None) -> datetime | None:
    """库里存的是不带时区的 UTC，fsrs 要带时区的，进出都得在这里换一次。"""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _to_naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


def _to_card(state: CardState) -> "Card":
    return Card(
        card_id=1,
        state=_DB_TO_FSRS.get(state.state, State.Learning),
        step=state.step or None,
        stability=state.stability or None,
        difficulty=state.difficulty or None,
        due=_to_aware(state.due),
        last_review=_to_aware(state.last_review),
    )


def _review_with_fsrs(state: CardState, rating: int) -> ScheduleResult | None:
    if not _HAS_FSRS:
        return None
    try:
        card = _to_card(state)
        new_card = _scheduler.review_card(card, getattr(Rating, RATING_NAMES[rating]))[0]

        now = utcnow()
        # fsrs 返回的是 aware UTC，统一换回库里用的 naive UTC 再相减
        due = _to_naive(new_card.due) or now
        interval = max(0.0, (due - now).total_seconds() / 86400)

        return ScheduleResult(
            state=CardState(
                stability=float(new_card.stability or 0),
                difficulty=float(new_card.difficulty or 0),
                state=_FSRS_TO_DB.get(new_card.state, 1),
                step=int(new_card.step or 0),
                interval_days=interval,
                reps=state.reps + 1,
                lapses=state.lapses + (1 if rating == 1 else 0),
                due=due,
                last_review=now,
            ),
            interval_days=interval,
            source="fsrs",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("FSRS 调用失败，改用内置调度器: %s", exc)
        return None


# ---------------------------------------------------------------- fallback

# 简易调度：够用、可预期，但不是最优。py-fsrs 正常时不会走到这里。
_FALLBACK_STEPS_MIN = {1: 5, 2: 10, 3: 25}
_MULTIPLIER = {1: 0.0, 2: 1.2, 3: 2.5, 4: 3.5}


def _review_fallback(state: CardState, rating: int) -> ScheduleResult:
    now = utcnow()
    lapses = state.lapses + (1 if rating == 1 else 0)

    if rating == 1:
        minutes = _FALLBACK_STEPS_MIN[1]
        interval = minutes / (60 * 24)
        new_state_no = 3 if state.state == 2 else 1
        step = 0
    elif state.interval_days <= 0 or state.state == 0:
        minutes = _FALLBACK_STEPS_MIN.get(rating, 10)
        interval = minutes / (60 * 24)
        new_state_no = 1
        step = min(state.step + 1, 2)
    else:
        interval = max(1.0, state.interval_days * _MULTIPLIER[rating])
        new_state_no = 2
        step = 0

    return ScheduleResult(
        state=CardState(
            stability=state.stability or interval,
            difficulty=state.difficulty,
            state=new_state_no,
            step=step,
            interval_days=interval,
            reps=state.reps + 1,
            lapses=lapses,
            due=now + timedelta(days=interval),
            last_review=now,
        ),
        interval_days=interval,
        source="fallback",
    )


def review(state: CardState, rating: int) -> ScheduleResult:
    """提交一次评分，返回新的卡片状态。rating 取 1~4。"""
    if rating not in RATING_NAMES:
        raise ValueError(f"rating 必须是 1~4，收到 {rating}")
    return _review_with_fsrs(state, rating) or _review_fallback(state, rating)


def is_available() -> bool:
    return _HAS_FSRS
