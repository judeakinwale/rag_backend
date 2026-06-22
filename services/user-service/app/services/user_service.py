from app.repositories.user_repository import UserRepository
from app.producers.user_producer import UserProducer
from app.core.uow import UnitOfWork


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

    async def create_user(self, email: str, name: str):
        async with self.uow:
            user = await self.repo.create(email, name)

            # ensure the user is persisted and
            await self.uow.session.flush()
            # access the persisted user's id before committing and sending the event
            user_id = user.id
            print(f"Created user with ID: {user_id}")
            print(f"User details: {user}")

        await self.producer.user_created(user)

        return user
