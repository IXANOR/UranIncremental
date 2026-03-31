from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return service liveness status.

    Returns:
        dict: Always ``{"status": "ok"}`` when the service is running.
    """
    return {"status": "ok"}
