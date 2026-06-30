import orjson
from app.repositories.user_repository import UserRepository
from app.producers.user_producer import UserProducer
from app.events.user_events import UserCreatedEvent, UserUpdatedEvent, UserDeletedEvent
from app.models.user import User
from app.core.redis import generate_cache_key, r
from app.dto.user_dto import CreateUserRequest, UpdateUserRequest, UserResponse
from rag_packages.shared.database.uow import UnitOfWork
from rag_packages.shared.database.query import QueryParams


class UserService:
    def __init__(
        self,
        uow: UnitOfWork,
        repo: UserRepository,
        producer: UserProducer,
        # outbox_repo: None = None,
    ):
        self.uow = uow
        self.repo = repo
        self.producer = producer

    async def get_users(
        self, params: QueryParams | None = None
    ) -> tuple[list[UserResponse], int]:
        cache_key = generate_cache_key(str("all"))
        cached = await r.get(cache_key)

        if cached is not None:
            try:
                # Ensure the cached data is valid JSON
                users, count = orjson.loads(cached)
                return [UserResponse.model_validate_json(user) for user in users], count

            except orjson.JSONDecodeError:
                print(
                    f"[user-service] Failed to decode cached data for key {cache_key}. Invalidating cache."
                )
                await r.delete(cache_key)  # invalidate corrupted cache

        users, count = await self.repo.get_all(params)
        valid_users = [UserResponse.model_validate(user) for user in users]

        await r.set(cache_key, orjson.dumps((valid_users, count)))
        return valid_users, count

    # TODO: confirm this works as expected
    async def create_user(self, payload: CreateUserRequest) -> UserResponse:
        async with self.uow:
            user: User = await self.repo.create(payload)

            # ensure the user is persisted and
            await self.uow.session.flush()
            # access the persisted user's id before committing and sending the event
            user_id = user.id
            print(f"Created user with ID: {user_id}")
            print(f"User details: {user}")

            # outbox_repo.add(
            #     event_type="user_created",
            #     payload={...}
            # )

        event = UserCreatedEvent.model_validate(user)
        await self.producer.user_created(event)

        return UserResponse.model_validate(user)

    async def get_user_by_id(self, user_id: int) -> UserResponse | None:
        cache_key = generate_cache_key(str(user_id))
        cached = await r.get(cache_key)

        if cached is not None:
            return UserResponse.model_validate_json(cached)

        user = await self.repo.get_by_id(user_id)
        if user is None:
            return None

        valid_user = UserResponse.model_validate(user)

        await r.set(cache_key, valid_user.model_dump_json())
        return valid_user

    async def update_user(
        self, user_id: int, payload: UpdateUserRequest
    ) -> UserResponse | None:
        async with self.uow:
            user: User | None = await self.repo.update(user_id, payload)
            if user is None:
                return None

        event = UserUpdatedEvent.model_validate(user)
        event.updated = list(payload.model_dump(exclude_unset=True).keys())
        await self.producer.user_updated(event)

        return UserResponse.model_validate(user)

    async def delete_user(self, user_id: int) -> UserResponse | None:
        async with self.uow:
            user: User | None = await self.repo.delete(user_id)
            if user is None:
                return None

        event = UserDeletedEvent.model_validate(user)
        await self.producer.user_deleted(event)

        return UserResponse.model_validate(user)
