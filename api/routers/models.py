from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/models/{model_id}/promote")
def promote_model(model_id: str):
    # Stub implementation. Later we will persist model metadata and mark is_current.
    raise HTTPException(status_code=501, detail="Promote not implemented yet")
