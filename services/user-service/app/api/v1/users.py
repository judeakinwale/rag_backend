from typing import Annotated
from fastapi import APIRouter, Depends, Request, status, Query
from app.dto.user_dto import (
    UserAPIResponse,
    CreateUserRequest,
    UpdateUserRequest,
    UserListAPIResponse,
)
from app.dependencies.user import (
    get_user_service,
    get_user_producer,
    UserService,
    UserProducer,
)
from rag_packages.shared.database.query import QueryParams


router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=UserListAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Get all users",
)
async def get_users(
    query: Annotated[QueryParams, Query()],
    service: UserService = Depends(get_user_service),
    producer: UserProducer = Depends(get_user_producer),
) -> UserListAPIResponse:
    users, count = await service.get_users(query)
    # await producer.test({"event_msg": "get_users_called"})

    return UserListAPIResponse(
        success=True,
        data=users,
        count=count,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=UserAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Create a new user",
)
async def create_user(
    request: Request,
    body: CreateUserRequest,
    service: UserService = Depends(get_user_service),
) -> UserAPIResponse:
    created_user = await service.create_user(body)

    return UserAPIResponse(
        success=True,
        data=created_user,
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
    user_id: int, service: UserService = Depends(get_user_service)
) -> UserAPIResponse:
    user = await service.get_user_by_id(user_id)

    return UserAPIResponse(
        success=True,
        data=user,
    )


update_kwargs = {
    "status_code": status.HTTP_200_OK,
    "response_model": UserAPIResponse,
    "response_model_exclude_none": True,
    "response_model_exclude_unset": True,
    "summary": "Update a user by ID",
}


@router.patch("/{user_id}", **update_kwargs)
@router.put("/{user_id}", **update_kwargs)
async def update_user(
    user_id: int,
    body: UpdateUserRequest,
    service: UserService = Depends(get_user_service),
) -> UserAPIResponse:
    updated_user = await service.update_user(user_id, body)

    return UserAPIResponse(
        success=True,
        data=updated_user,
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Delete a user by ID",
)
async def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
) -> UserAPIResponse:
    deleted_user = await service.delete_user(user_id)

    return UserAPIResponse(
        success=True,
        data=deleted_user,
        message=f"User with ID {user_id} has been deleted.",
    )
