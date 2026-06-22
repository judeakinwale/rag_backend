from app.services.user_service import UserService
from app.repositories.user_repository import UserRepository
from app.producers.user_producer import UserProducer


class Container:
    def user_service(self, db):
        repo = UserRepository(db)
        producer = UserProducer()
        return UserService(repo=repo, producer=producer)


container = Container()
