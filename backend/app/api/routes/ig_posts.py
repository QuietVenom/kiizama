from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_active_superuser, get_posts_collection
from app.crud.posts import (
    create_post,
    delete_post,
    get_post,
    list_posts,
    replace_post,
    update_post,
)
from app.schemas import Post, PostCollection, UpdatePost

router = APIRouter(
    prefix="/ig-posts",
    tags=["ig-posts"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.post("/", response_model=Post, status_code=status.HTTP_201_CREATED)
async def create_ig_post(
    post: Post, collection: Any = Depends(get_posts_collection)
) -> Post:
    return await create_post(collection, post)


@router.get("/", response_model=PostCollection)
async def read_ig_posts(
    skip: int = 0,
    limit: int = 100,
    collection: Any = Depends(get_posts_collection),
) -> PostCollection:
    posts = await list_posts(collection, skip=skip, limit=limit)
    return PostCollection(posts=posts)


@router.get("/{post_id}", response_model=Post)
async def read_ig_post(
    post_id: str, collection: Any = Depends(get_posts_collection)
) -> Post:
    post = await get_post(collection, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.patch("/{post_id}", response_model=Post)
async def update_ig_post(
    post_id: str,
    patch: UpdatePost,
    collection: Any = Depends(get_posts_collection),
) -> Post:
    post = await update_post(collection, post_id, patch)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.put("/{post_id}", response_model=Post)
async def replace_ig_post(
    post_id: str,
    post_in: Post,
    collection: Any = Depends(get_posts_collection),
) -> Post:
    post = await replace_post(collection, post_id, post_in)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.delete("/{post_id}", response_model=Post)
async def delete_ig_post(
    post_id: str, collection: Any = Depends(get_posts_collection)
) -> Post:
    post = await delete_post(collection, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


__all__ = ["router"]
