from dataclasses import dataclass

from app.game_context import GameContextResolver
from app.llm import ChatTurnParser, LLMAdapter, StructuredOutputParser, TransportClient
from app.repositories import (
    CharacterRepository,
    FileRepositoryPaths,
    GameRepository,
    LLMLogRepository,
    MemoryRepository,
    NovelRepository,
    PlayerRepository,
    RelationRepository,
    SaveRepository,
    SessionRepository,
    SnapshotRepository,
)
from app.services.character_service import CharacterService
from app.services.check_service import CheckService
from app.services.game_service import GameService
from app.services.novel_service import NovelService
from app.services.player_service import PlayerService
from app.services.prompt_composer import PromptComposer
from app.services.save_service import SaveService


@dataclass(frozen=True)
class AppContainer:
    paths: FileRepositoryPaths
    session_repository: SessionRepository
    game_repository: GameRepository
    memory_repository: MemoryRepository
    player_repository: PlayerRepository
    character_repository: CharacterRepository
    relation_repository: RelationRepository
    snapshot_repository: SnapshotRepository
    save_repository: SaveRepository
    novel_repository: NovelRepository
    llm_log_repository: LLMLogRepository
    llm_adapter: LLMAdapter
    context_resolver: GameContextResolver
    prompt_composer: PromptComposer
    game_service: GameService
    character_service: CharacterService
    player_service: PlayerService
    save_service: SaveService
    check_service: CheckService
    novel_service: NovelService


def build_container() -> AppContainer:
    paths = FileRepositoryPaths()
    session_repository = SessionRepository(paths)
    game_repository = GameRepository(paths)
    memory_repository = MemoryRepository(paths)
    player_repository = PlayerRepository(paths)
    character_repository = CharacterRepository(paths)
    relation_repository = RelationRepository(paths)
    snapshot_repository = SnapshotRepository(paths)
    save_repository = SaveRepository(paths)
    novel_repository = NovelRepository(paths)
    llm_log_repository = LLMLogRepository(paths)

    llm_adapter = LLMAdapter(
        transport=TransportClient(),
        json_parser=StructuredOutputParser(),
        chat_parser=ChatTurnParser(StructuredOutputParser()),
        llm_log_repository=llm_log_repository,
    )

    prompt_composer = PromptComposer(
        memory_repository=memory_repository,
        player_repository=player_repository,
        character_repository=character_repository,
    )
    player_service = PlayerService(player_repository=player_repository, llm_adapter=llm_adapter)
    game_service = GameService(
        prompt_composer=prompt_composer,
        memory_repository=memory_repository,
        character_repository=character_repository,
        relation_repository=relation_repository,
        llm_adapter=llm_adapter,
    )
    character_service = CharacterService(
        character_repository=character_repository,
        relation_repository=relation_repository,
        snapshot_repository=snapshot_repository,
        llm_adapter=llm_adapter,
    )
    save_service = SaveService(save_repository=save_repository)
    check_service = CheckService(player_repository=player_repository, player_service=player_service)
    novel_service = NovelService(
        memory_repository=memory_repository,
        save_repository=save_repository,
        novel_repository=novel_repository,
        llm_adapter=llm_adapter,
    )
    context_resolver = GameContextResolver(session_repository, game_repository)

    return AppContainer(
        paths=paths,
        session_repository=session_repository,
        game_repository=game_repository,
        memory_repository=memory_repository,
        player_repository=player_repository,
        character_repository=character_repository,
        relation_repository=relation_repository,
        snapshot_repository=snapshot_repository,
        save_repository=save_repository,
        novel_repository=novel_repository,
        llm_log_repository=llm_log_repository,
        llm_adapter=llm_adapter,
        context_resolver=context_resolver,
        prompt_composer=prompt_composer,
        game_service=game_service,
        character_service=character_service,
        player_service=player_service,
        save_service=save_service,
        check_service=check_service,
        novel_service=novel_service,
    )


container = build_container()
