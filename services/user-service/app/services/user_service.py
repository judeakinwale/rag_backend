from app.repositories.user_repository import UserRepository
from app.producers.user_producer import UserProducer
from app.events.user_events import UserCreatedEvent, UserUpdatedEvent, UserDeletedEvent
from app.models.user import User
from app.dto.user_dto import CreateUserRequest, UpdateUserRequest, UserResponse
from rag_packages.shared.database.uow import UnitOfWork


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

    async def get_users(self) -> list[UserResponse]:
        users = await self.repo.get_all()
        return [UserResponse.model_validate(user) for user in users]

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
        user = await self.repo.get_by_id(user_id)
        if user is None:
            return None
        return UserResponse.model_validate(user)

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
