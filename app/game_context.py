from dataclasses import dataclass
from typing import Optional

from fastapi import Request
from starlette.websockets import WebSocket

from app.request_context import get_request_id


@dataclass(frozen=True)
class GameContext:
    game_id: str
    session_id: Optional[str] = None
    request_id: Optional[str] = None


class GameContextResolver:
    def __init__(self, session_repository, game_repository):
        self.session_repository = session_repository
        self.game_repository = game_repository

    def get_session_id_from_request(self, request: Request) -> Optional[str]:
        return request.headers.get("X-Adventure-Session-ID") or request.cookies.get(
            "adventure_session_id"
        )

    def get_session_id_from_websocket(self, websocket: WebSocket) -> Optional[str]:
        return websocket.query_params.get("session_id")

    def build_context(
        self,
        game_id: Optional[str],
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Optional[GameContext]:
        if not game_id:
            return None
        return GameContext(
            game_id=game_id,
            session_id=session_id,
            request_id=request_id or get_request_id(),
        )

    def resolve_from_session(
        self, session_id: Optional[str], request_id: Optional[str] = None
    ) -> Optional[GameContext]:
        game_id = self.session_repository.resolve_active_game(
            session_id, self.game_repository
        )
        return self.build_context(game_id, session_id=session_id, request_id=request_id)

    def resolve_optional(self, request: Request) -> Optional[GameContext]:
        return self.resolve_from_session(
            self.get_session_id_from_request(request), request_id=get_request_id()
        )

    def resolve_required(self, request: Request) -> GameContext:
        ctx = self.resolve_optional(request)
        if ctx is None:
            raise RuntimeError("没有活动的游戏，请先创建或加载游戏")
        return ctx

    def resolve_optional_websocket(self, websocket: WebSocket) -> Optional[GameContext]:
        return self.resolve_from_session(self.get_session_id_from_websocket(websocket))

    def resolve_required_websocket(self, websocket: WebSocket) -> GameContext:
        ctx = self.resolve_optional_websocket(websocket)
        if ctx is None:
            raise RuntimeError("没有活动的游戏，请先创建或加载游戏")
        return ctx
