from fastapi import APIRouter, Depends, Request, status
from app.core.db import get_db
from app.core.container import container
from app.dto.user_dto import UserAPIResponse, CreateUserRequest, UserListAPIResponse
from app.dependencies.user import get_user_service, get_user_producer, UserService
from rag_packages.shared.kafka.producer import KafkaProducer

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=UserListAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Get all users",
)
async def get_users(
    service: UserService = Depends(get_user_service),
    producer: KafkaProducer = Depends(get_user_producer),
) -> UserListAPIResponse:
    users = await service.get_users()
    
    return UserListAPIResponse(
        success=True,
        data=users,
    )


# async def get_users(request: Request, db=Depends(get_db)) -> UserListAPIResponse:
#     producer: KafkaProducer = request.app.state.kafka_producer
#     service = container.user_service(db, kafka_producer=producer)
#     users = await service.get_users()

#     return UserListAPIResponse(
#         success=False,
#         data=users,
#     )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=UserAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Create a new user",
)
async def create_user(
    request: Request, body: CreateUserRequest, db=Depends(get_db)
) -> UserAPIResponse:
    producer: KafkaProducer = request.app.state.kafka_producer
    service = container.user_service(db, kafka_producer=producer)
    created_user = await service.create_user(body)

    return UserAPIResponse(
        success=True,
        data=created_user,
        message="created",
    )


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Get a user by ID",
)
async def get_user(
    request: Request, user_id: int, db=Depends(get_db)
) -> UserAPIResponse:
    producer: KafkaProducer = request.app.state.kafka_producer
    service = container.user_service(db, kafka_producer=producer)
    user = await service.get_user_by_id(user_id)

    return UserAPIResponse(
        success=True,
        data=user,
    ).model_dump(exclude_none=True)
