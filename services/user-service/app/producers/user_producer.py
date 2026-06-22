from app.kafka_producer import producer


class UserProducer:
    async def user_created(self, user):
        await producer.send(
            "user.created",
            {
                "id": user.id,
                "email": user.email,
            },
        )
